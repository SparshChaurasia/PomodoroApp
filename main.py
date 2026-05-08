import tkinter as tk
from tkinter import messagebox
import ctypes
import os
import sys
import winsound
import json
import csv
import math
from datetime import datetime, timedelta
import random
import subprocess

def get_app_path(filename: str) -> str:
    """Returns the absolute path to a file, suitable for both dev and PyInstaller EXE."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

# ── Constants ──────────────────────────────────────────────────────────────────
BG_COLOR    = "#333235"
BTN_COLOR   = "#4cc2ff"
FONT_MAIN   = ("Fira Code", 35, "bold")
FONT_BTN    = ("Fira Code", 11, "bold")
FONT_LABEL  = ("Fira Code", 10)
FONT_CLOSE  = ("Fira Code", 8)
CONFIG_NAME = "config.json"
STATS_NAME  = "stats.json"

DEFAULTS = {
    "focus_min":    25,
    "break_min":    5,
    "break_auto":   True,
    "auto_inc_val": 2,
    "inc_threshold": 5,
    "max_focus_min": 60,
    "daily_target_hrs": 8,
}

BREAK_TASKS = [
    "Do 5 pushups to re-energize.",
    "Stretch your arms and shoulders.",
    "Close your eyes and meditate for 60 seconds.",
    "Take a quick walk around the room.",
    "Hydrate! Drink a glass of water.",
    "Practice 1 minute of deep breathing.",
    "Rest your eyes: Look at something 20 feet away.",
    "Do 10 jumping jacks for a quick boost.",
    "Perform a quick neck and wrist stretch."
]

# ── UI Constants ───────────────────────────────────────────────────────────────
DIALOG_WIDTH  = 270
DIALOG_HEIGHT = 310
WIN_W, WIN_H  = 220, 240
TITLE_H       = 36
DIVIDER_COLOR = "#3e3c40"
OUTLINE_COLOR = "#555558"

# ── Business Logic & Data Managers (SOLID) ───────────────────────────────────

class SettingsManager:
    """Handles persistence of application configuration."""
    def __init__(self, filename: str):
        self.path = get_app_path(filename)
        self.data = DEFAULTS.copy()
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self.data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=4)
        except OSError as e:
            print(f"Failed to save settings: {e}")

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()

    @property
    def focus_min(self): return self.data["focus_min"]
    @property
    def break_min(self): return self.data["break_min"]
    @property
    def auto_inc_val(self): return self.data["auto_inc_val"]
    @property
    def inc_threshold(self): return self.data["inc_threshold"]
    @property
    def max_focus_min(self): return self.data["max_focus_min"]
    @property
    def daily_target_hrs(self): return self.data.get("daily_target_hrs", 8)

class StatsManager:
    """Handles daily focus time tracking with session granularity."""
    def __init__(self, filename: str):
        self.path = get_app_path(filename)
        self.data = {}
        self.load()
    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.data = json.loads(content)
                    else:
                        self.data = {}
            except (json.JSONDecodeError, OSError):
                self.data = {}
        else:
            self.data = {}

    def record_focus(self, seconds: int):
        if seconds <= 0: return
        now = datetime.now()
        date_str = str(now.date())
        time_str = now.strftime("%H:%M:%S")

        if date_str not in self.data:
            self.data[date_str] = {"total": 0, "sessions": []}
        
        self.data[date_str]["total"] += seconds
        self.data[date_str]["sessions"].append({"t": time_str, "d": seconds})
        self.save()

    def save(self):
        try:
            temp_path = self.path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(self.data, f, indent=4)
            os.replace(temp_path, self.path)
        except OSError:
            pass

    @property
    def stats(self):
        """Returns a compatible dict of {date: total_seconds} for the UI."""
        res = {}
        if not isinstance(self.data, dict):
            return res
        for d, info in self.data.items():
            if isinstance(info, dict):
                res[d] = info.get("total", 0)
            elif isinstance(info, (int, float)):
                res[d] = int(info)
        return res

class TimerEngine:
    """Core timer logic, independent of UI components."""
    def __init__(self, settings: SettingsManager, on_tick=None, on_end=None):
        self.settings = settings
        self.on_tick = on_tick
        self.on_end = on_end
        
        self.running = False
        self.is_focus = True
        self.completed_sessions = 0
        self.remaining_seconds = 0
        self.initial_seconds = 0
        
        self.reset_to_focus()

    def reset_to_focus(self):
        self.running = False
        self.is_focus = True
        self.remaining_seconds = self.settings.focus_min * 60
        self.initial_seconds = self.remaining_seconds

    def tick(self):
        if not self.running: return
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            if self.on_tick: self.on_tick()
        else:
            self.end_period()

    def end_period(self):
        self.running = False
        if self.on_end: self.on_end()

    def start(self): self.running = True
    def stop(self):  self.running = False

    def skip(self):
        self.running = False
        if self.is_focus:
            self.transition_to_break()
        else:
            self.transition_to_focus()

    def transition_to_break(self):
        self.completed_sessions += 1
        # Auto-increment logic
        if self.completed_sessions % self.settings.inc_threshold == 0:
            current_f = self.settings.data["focus_min"]
            if current_f < self.settings.max_focus_min:
                new_f = min(current_f + self.settings.auto_inc_val, self.settings.max_focus_min)
                self.settings.update(focus_min=new_f, break_min=compute_break(new_f))
        
        self.is_focus = False
        if self.settings.data.get("break_auto", True):
            # Calculate break based on current focus_min
            from_settings = compute_break(self.settings.focus_min)
            self.remaining_seconds = from_settings * 60
        else:
            self.remaining_seconds = self.settings.break_min * 60
        self.initial_seconds = self.remaining_seconds

    def transition_to_focus(self):
        self.is_focus = True
        self.remaining_seconds = self.settings.focus_min * 60
        self.initial_seconds = self.remaining_seconds

# ── UI Helpers ───────────────────────────────────────────────────────────────
def show_in_taskbar(root: tk.Tk) -> None:
    """Force a frameless (overrideredirect) window onto the Windows taskbar."""
    if os.name != "nt":
        return
    try:
        hwnd  = ctypes.windll.user32.GetParent(root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        style = (style & ~0x00000080) | 0x00040000               # RM TOOLWINDOW, ADD APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        root.withdraw()
        root.after(10, root.deiconify)
    except Exception:
        pass


def compute_break(focus_min: int) -> int:
    """Return the appropriate break length based on focus duration."""
    if focus_min <= 10:
        return 2
    if focus_min <= 20:
        return 5
    if focus_min < 60:
        return 10
    return 15


def draw_rounded_window_bg(canvas: tk.Canvas, w: int, h: int, r: int, fill: str, outline: str) -> None:
    """Draw a rounded rectangle with a border on a canvas."""
    canvas.delete("all")
    # Fill corners and body
    canvas.create_oval(0, 0, 2*r, 2*r, fill=fill, outline=fill)
    canvas.create_oval(w-2*r, 0, w, 2*r, fill=fill, outline=fill)
    canvas.create_oval(0, h-2*r, 2*r, h, fill=fill, outline=fill)
    canvas.create_oval(w-2*r, h-2*r, w, h, fill=fill, outline=fill)
    canvas.create_rectangle(r, 0, w-r, h, fill=fill, outline=fill)
    canvas.create_rectangle(0, r, w, h-r, fill=fill, outline=fill)
    
    # Border
    canvas.create_arc(0, 0, 2*r-1, 2*r-1, start=90, extent=90, outline=outline, style="arc")
    canvas.create_arc(w-2*r, 0, w-1, 2*r-1, start=0, extent=90, outline=outline, style="arc")
    canvas.create_arc(w-2*r, h-2*r, w-1, h-1, start=270, extent=90, outline=outline, style="arc")
    canvas.create_arc(0, h-2*r, 2*r-1, h-1, start=180, extent=90, outline=outline, style="arc")
    
    canvas.create_line(r, 0, w-r, 0, fill=outline)
    canvas.create_line(r, h-1, w-r, h-1, fill=outline)
    canvas.create_line(0, r, 0, h-r, fill=outline)
    canvas.create_line(w-1, r, w-1, h-r, fill=outline)



def draw_timer_box(canvas: tk.Canvas, w: int, h: int, r: int) -> None:
    """Draw a clean background box that matches the main app background."""
    canvas.delete("timer_bg")
    # Using the exact same color as the rest of the background for a seamless look
    fill_col = BG_COLOR
    
    # We only draw the fill to ensure the text has a clean area, 
    # but since it's the same color as BG_COLOR, it will be seamless.
    canvas.create_rectangle(r, 0, w-r, h, fill=fill_col, outline="", tags="timer_bg")
    canvas.create_rectangle(0, r, w, h-r, fill=fill_col, outline="", tags="timer_bg")
    canvas.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=fill_col, outline="", tags="timer_bg")
    canvas.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=fill_col, outline="", tags="timer_bg")
    canvas.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=fill_col, outline="", tags="timer_bg")
    canvas.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=fill_col, outline="", tags="timer_bg")


# ── Widgets ────────────────────────────────────────────────────────────────────
class RoundedButton(tk.Canvas):
    """A canvas-based button with rounded corners and hover/press effects."""

    HOVER_COLOR = "#60ccff"
    PRESS_COLOR = "#3da8e6"

    def __init__(
        self,
        parent,
        text: str,
        command,
        width: int = 60,
        height: int = 35,
        radius: int = 8,
        color: str = BTN_COLOR,
        bg: str = BG_COLOR,
        font=FONT_BTN,
        rounded: tuple = (True, True, True, True), # (tl, tr, br, bl)
        border_edges: tuple = (False, False, False, False) # (top, right, bottom, left)
    ):
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0)
        self._command = command
        self._color   = color
        self._radius  = radius
        self._text    = text
        self._font    = font
        self._btn_w = width
        self._btn_h = height
        self._rounded = rounded
        self._border_edges = border_edges

        self._create_items()
        self.bind("<Button-1>",        lambda _: self._update_ui(self.PRESS_COLOR))
        self.bind("<ButtonRelease-1>", lambda _: self._on_release())
        self.bind("<Enter>",           lambda _: self._update_ui(self.HOVER_COLOR))
        self.bind("<Leave>",           lambda _: self._update_ui(self._color))

    def _create_items(self) -> None:
        """Create all canvas elements once for efficient reuse."""
        w, h, r = self._btn_w, self._btn_h, self._radius
        top_left, top_right, bot_right, bot_left = self._rounded
        border_top, border_right, border_bottom, border_left = self._border_edges
        outline_color = OUTLINE_COLOR
        color = self._color

        # Fill items (Tagged with 'fill')
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color, tags="fill")
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color, tags="fill")
        
        # Corners Fill
        corners = [
            (top_left,  0,       0,       r*2,     r*2),
            (top_right, w - r*2, 0,       w,       r*2),
            (bot_right, w - r*2, h - r*2, w,       h),
            (bot_left,  0,       h - r*2, r*2,     h)
        ]
        for is_rounded, x0, y0, x1, y1 in corners:
            if is_rounded:
                self.create_oval(x0, y0, x1, y1, fill=color, outline=color, tags="fill")
            else:
                # Square corner fill
                sx0 = x0 if x1 <= r*2 else x1-r
                sy0 = y0 if y1 <= r*2 else y1-r
                self.create_rectangle(sx0, sy0, sx0+r, sy0+r, fill=color, outline=color, tags="fill")

        # Outline items (Static - drawn once)
        if border_top:    self.create_line(r if top_left else 0,  0, w - r if top_right else w, 0, fill=outline_color)
        if border_bottom: self.create_line(r if bot_left else 0,  h - 1, w - r if bot_right else w, h - 1, fill=outline_color)
        if border_left:   self.create_line(0, r if top_left else 0,  0, h - r if bot_left else h, fill=outline_color)
        if border_right:  self.create_line(w - 1, r if top_right else 0, w - 1, h - r if bot_right else h, fill=outline_color)

        # Arcs for rounded corners
        if top_left and border_top and border_left:
            self.create_arc(0, 0, r*2-1, r*2-1, start=90, extent=90, outline=outline_color, style="arc")
        if top_right and border_top and border_right:
            self.create_arc(w-r*2, 0, w-1, r*2-1, start=0, extent=90, outline=outline_color, style="arc")
        if bot_right and border_bottom and border_right:
            self.create_arc(w-r*2, h-r*2, w-1, h-1, start=270, extent=90, outline=outline_color, style="arc")
        if bot_left and border_bottom and border_left:
            self.create_arc(0, h-r*2, r*2-1, h-1, start=180, extent=90, outline=outline_color, style="arc")

        self._text_item = self.create_text(w/2, h/2, text=self._text, fill="white", font=self._font)

    def _update_ui(self, color: str) -> None:
        """Update existing item colors."""
        self.itemconfig("fill", fill=color, outline=color)

    def _on_release(self) -> None:
        self._update_ui(self._color)
        if self._command:
            self._command()

    def update(self, text: str = None, color: str = None) -> None:
        """Update label text and/or color."""
        if text:
            self._text = text
            self.itemconfig(self._text_item, text=text)
        if color:
            self._color = color
            self._update_ui(color)


# ── Generic Dialogs ────────────────────────────────────────────────────────────
class DraggableWindow(tk.Toplevel):
    """Base class for frameless, draggable windows with rounded corners."""
    def __init__(self, parent, width: int, height: int):
        super().__init__(parent)
        self.overrideredirect(True)
        self.geometry(f"{width}x{height}")
        self.wm_attributes("-topmost", True)

        # Rounded corners setup
        self.config(bg="#000001")
        self.wm_attributes("-transparentcolor", "#000001")

        self.bg_canvas = tk.Canvas(self, width=width, height=height, bg="#000001", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)
        draw_rounded_window_bg(self.bg_canvas, width, height, 12, BG_COLOR, "#aaaaaa")

        # Bindings for dragging
        self.bg_canvas.bind("<Button-1>", self._drag_start)
        self.bg_canvas.bind("<B1-Motion>", self._drag_move)
        self.bind("<Button-1>", self._drag_start)
        self.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event):
        self._drag_x, self._drag_y = event.x, event.y

    def _drag_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")


# ── Settings window ────────────────────────────────────────────────────────────
class SettingsWindow(DraggableWindow):
    """A frameless, draggable Toplevel for editing app settings."""

    def __init__(self, parent: tk.Misc, timer: "PomodoroTimer"):
        super().__init__(parent, DIALOG_WIDTH, DIALOG_HEIGHT + 40)
        self._timer = timer
        self._build_ui()

    def _build_ui(self) -> None:
        t = self._timer

        # Title and Close button
        tk.Label(self, text="SETTINGS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR
                 ).place(x=DIALOG_WIDTH//2, y=18, anchor="center")
        
        tk.Button(self, text="×", font=("Segoe UI", 12), command=self.destroy,
                  bg=BG_COLOR, fg="#888888", bd=0, activebackground=BG_COLOR,
                  activeforeground="#ff5f57", cursor="hand2", padx=0, pady=0
                  ).place(x=DIALOG_WIDTH - 18, y=18, anchor="center")

        # Top horizontal divider
        tk.Frame(self, height=1, bg=DIVIDER_COLOR).pack(fill="x", padx=0, pady=(35, 0))

        # Rows with 10px top padding for the first element to match timer spacing
        self._f  = self._make_row("Focus", t.settings.focus_min, first=True)
        
        # Break row with Auto checkbox
        self._break_auto_var = tk.BooleanVar(value=t.settings.data.get("break_auto", True))
        self._b, self._b_chk = self._make_row_with_auto("Break", t.settings.break_min, self._break_auto_var)
        
        self._a  = self._make_row("Increment By", t.settings.auto_inc_val)
        self._th = self._make_row("Increment Every", t.settings.inc_threshold)
        self._mf = self._make_row("Max Focus", t.settings.max_focus_min)
        self._dt = self._make_row("Daily Target (h)", t.settings.daily_target_hrs)

        RoundedButton(self, text="💾 Save", command=self._save,
                      color=BTN_COLOR, width=DIALOG_WIDTH - 40).pack(pady=15)

    def _make_row_with_auto(self, label: str, value, var: tk.BooleanVar) -> tuple[tk.Entry, tk.Checkbutton]:
        row = tk.Frame(self, bg=BG_COLOR)
        row.pack(fill="x", padx=20, pady=5)
        tk.Label(row, text=label, bg=BG_COLOR, fg="white", font=FONT_LABEL).pack(side="left")
        
        entry = tk.Entry(row, width=8, bg="#444345", fg="white", bd=0,
                         highlightthickness=1, highlightbackground="#555",
                         insertbackground="white")
        entry.insert(0, str(value))
        entry.pack(side="right")
        
        chk = tk.Checkbutton(row, text="Auto", variable=var, bg=BG_COLOR, fg=BTN_COLOR, 
                             selectcolor=BG_COLOR, activebackground=BG_COLOR, 
                             activeforeground=BTN_COLOR, font=("Fira Code", 8),
                             command=lambda: entry.config(state="disabled" if var.get() else "normal"))
        chk.pack(side="right", padx=(0, 5))
        
        if var.get(): entry.config(state="disabled")
        return entry, chk

    def _make_row(self, label: str, value, first: bool = False) -> tk.Entry:
        row = tk.Frame(self, bg=BG_COLOR)
        row.pack(fill="x", padx=20, pady=((10 if first else 5), 5))
        tk.Label(row, text=label, bg=BG_COLOR, fg="white", font=FONT_LABEL).pack(side="left")
        entry = tk.Entry(row, width=8, bg="#444345", fg="white", bd=0,
                         highlightthickness=1, highlightbackground="#555",
                         insertbackground="white")
        entry.insert(0, str(value))
        entry.pack(side="right")
        return entry

    def _save(self) -> None:
        try:
            self._timer.apply_settings(
                focus_min    = int(self._f.get()),
                break_min    = int(self._b.get()) if not self._break_auto_var.get() else compute_break(int(self._f.get())),
                break_auto   = self._break_auto_var.get(),
                auto_inc_val = int(self._a.get()),
                inc_threshold= int(self._th.get()),
                max_focus_min= int(self._mf.get()),
                daily_target_hrs= float(self._dt.get()),
            )
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number !", parent=self)


# ── Stats window ───────────────────────────────────────────────────────────────
class StatsWindow(DraggableWindow):
    """A frameless, draggable Toplevel for viewing weekly focus history."""

    def __init__(self, parent: tk.Misc, timer: "PomodoroTimer"):
        super().__init__(parent, DIALOG_WIDTH, DIALOG_HEIGHT + 20)
        self._timer = timer
        self._stats = timer.stats_mgr.stats
        self._build_ui()

    def _build_ui(self) -> None:
        # Title and Close button
        tk.Label(self, text="STATISTICS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR
                 ).place(x=DIALOG_WIDTH//2, y=18, anchor="center")
        
        tk.Button(self, text="×", font=("Segoe UI", 12), command=self.destroy,
                  bg=BG_COLOR, fg="#888888", bd=0, activebackground=BG_COLOR,
                  activeforeground="#ff5f57", cursor="hand2", padx=0, pady=0
                  ).place(x=DIALOG_WIDTH - 18, y=18, anchor="center")

        # Top horizontal divider
        tk.Frame(self, height=1, bg=DIVIDER_COLOR).pack(fill="x", padx=0, pady=(35, 0))

        # Stats Summary
        header = tk.Frame(self, bg=BG_COLOR)
        header.pack(fill="x", padx=20, pady=10)

        today_date = str(datetime.now().date())
        today_secs = self._stats.get(today_date, 0)
        
        now = datetime.now().date()
        week_secs = sum(self._stats.get(str(now - timedelta(days=i)), 0) for i in range(7))
        target_hrs = self._timer.settings.daily_target_hrs

        def make_stat(parent, label, value, row, col):
            f = tk.Frame(parent, bg=BG_COLOR)
            f.grid(row=row, column=col, sticky="w", padx=5)
            tk.Label(f, text=label, font=("Fira Code", 8), fg="#888", bg=BG_COLOR).pack(anchor="w")
            tk.Label(f, text=value, font=("Fira Code", 10, "bold"), fg="white", bg=BG_COLOR).pack(anchor="w")

        make_stat(header, "TODAY", f"{today_secs/3600:.1f}h", 0, 0)
        make_stat(header, "WEEK", f"{week_secs/3600:.1f}h", 0, 1)

        t_frame = tk.Frame(header, bg=BG_COLOR)
        t_frame.grid(row=0, column=2, sticky="w", padx=5)
        tk.Label(t_frame, text="TARGET(h)", font=("Fira Code", 8), fg=BTN_COLOR, bg=BG_COLOR).pack(anchor="w")
        self._t_entry = tk.Entry(t_frame, width=4, bg="#444345", fg="white", bd=0, highlightthickness=1, 
                                highlightbackground="#555", insertbackground="white", font=("Fira Code", 9, "bold"))
        self._t_entry.insert(0, str(target_hrs))
        self._t_entry.pack(side="left")
        tk.Button(t_frame, text="ok", font=("Fira Code", 7), bg=BG_COLOR, fg="#888", bd=0, command=self._save_t).pack(side="left")

        header.columnconfigure((0,1,2), weight=1)
        tk.Frame(self, height=1, bg=DIVIDER_COLOR).pack(fill="x", padx=20, pady=5)

        # Scrollable area
        container = tk.Frame(self, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=(20, 5), pady=(0, 10))
        canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
        sb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_COLOR)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scroll_frame, anchor="nw", width=DIALOG_WIDTH-50)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        days = [(now - timedelta(days=i)) for i in range(13, -1, -1)]
        max_val = max([self._stats.get(str(d), 0) for d in days] + [target_hrs*3600, 3600])

        for d in days:
            val = self._stats.get(str(d), 0)
            row = tk.Frame(scroll_frame, bg=BG_COLOR)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=d.strftime("%a %d/%m"), font=("Fira Code", 8), fg="#888", bg=BG_COLOR, width=10, anchor="w").pack(side="left")
            bar_bg = tk.Frame(row, bg="#2a2a2c", height=12)
            bar_bg.pack(side="left", fill="x", expand=True, padx=5)
            pct = min(val/max_val, 1.0)
            if val > 0:
                color = BTN_COLOR if val >= (target_hrs*3600) else "#50a0c0"
                tk.Frame(bar_bg, bg=color, height=12).place(relx=0, rely=0, relwidth=pct)
            tk.Label(row, text=f"{val/3600:.1f}h", font=("Fira Code", 8), fg="white", bg=BG_COLOR, width=4).pack(side="right")

    def _save_t(self) -> None:
        try:
            self._timer.settings.update(daily_target_hrs=float(self._t_entry.get()))
            self._t_entry.config(highlightbackground=BTN_COLOR)
        except: pass


class ToastWindow(DraggableWindow):
    """A professional-looking non-blocking notification that mimics Windows Toasts."""
    def __init__(self, parent, title: str, message: str, buttons: list):
        # Width 320, Height 140 (enough for text + buttons)
        w, h = 320, 140
        super().__init__(parent, w, h)
        
        # Position at bottom right (above taskbar)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")
        
        # Override background color for a "toast" feel (slightly lighter)
        self.bg_canvas.delete("all")
        draw_rounded_window_bg(self.bg_canvas, w, h, 12, "#3d3c3f", "#555")

        # Icon/Logo (optional, using text for now)
        tk.Label(self, text="🔔", font=("Segoe UI Symbol", 14), fg=BTN_COLOR, bg="#3d3c3f").place(x=20, y=20)
        
        # Title
        tk.Label(self, text=title.upper(), font=("Fira Code", 9, "bold"), fg=BTN_COLOR, bg="#3d3c3f").place(x=55, y=20)
        
        # Message
        msg_lbl = tk.Label(self, text=message, font=("Segoe UI", 9), fg="white", bg="#3d3c3f", 
                           justify="left", wraplength=280)
        msg_lbl.place(x=25, y=50)

        # Buttons
        btn_frame = tk.Frame(self, bg="#3d3c3f")
        btn_frame.place(x=w-20, y=h-20, anchor="se")
        
        for btn_info in reversed(buttons):
            cmd = btn_info["command"]
            # Wrap command to also destroy the toast
            def make_cmd(c=cmd):
                if c: c()
                self.destroy()
            
            b = RoundedButton(btn_frame, text=btn_info["text"], command=make_cmd,
                              width=90, height=28, radius=6, color="#4c4b4e", bg="#3d3c3f",
                              font=("Segoe UI", 8, "bold"))
            b.pack(side="right", padx=5)

        # Auto-close after 10 seconds if no action
        self.after(10000, self.destroy)
        winsound.MessageBeep(winsound.MB_ICONASTERISK)


# ── Main app ───────────────────────────────────────────────────────────────────
class PomodoroTimer:
    """Main application controller (UI focus)."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._timer_id: str | None = None

        # SOLID Managers
        self.settings = SettingsManager(CONFIG_NAME)
        self.stats_mgr = StatsManager(STATS_NAME)
        self.engine = TimerEngine(self.settings, on_tick=self._refresh_display, on_end=self._on_period_end)
        self._is_mini = False

        self._configure_window()
        self._build_ui()
        self._refresh_display()

    def _configure_window(self) -> None:
        self.root.title("Pomodoro")
        w, h = WIN_W, WIN_H
        self.root.geometry(f"{w}x{h}")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        self.root.config(bg="#000001")
        self.root.wm_attributes("-transparentcolor", "#000001")

        self.bg_canvas = tk.Canvas(self.root, width=w, height=h, bg="#000001", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)
        draw_rounded_window_bg(self.bg_canvas, w, h, 12, BG_COLOR, OUTLINE_COLOR)

        self.root.after(50, lambda: show_in_taskbar(self.root))
        self.bg_canvas.bind("<Button-1>", self._drag_start)
        self.bg_canvas.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event) -> None:
        self._drag_x, self._drag_y = event.x, event.y

    def _drag_move(self, event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        for child in self.root.winfo_children():
            if child != self.bg_canvas:
                child.destroy()

        _btn = dict(bg=BG_COLOR, bd=0, activebackground=BG_COLOR, cursor="hand2")

        # Left icons
        tk.Button(self.root, text="⚙", font=("Segoe UI Symbol", 10), fg="#888", activeforeground="white",
                  command=self._open_settings, **_btn).place(x=15, y=18, anchor="center")
        tk.Button(self.root, text="▦", font=("Segoe UI Symbol", 10), fg="#888", activeforeground="white",
                  command=self._open_stats, **_btn).place(x=40, y=18, anchor="center")

        # Right window controls
        tk.Button(self.root, text="─", font=("Segoe UI", 10), fg="#888", activeforeground="white",
                  command=self._toggle_mini_mode, padx=0, pady=0, **_btn).place(x=178, y=18, anchor="center")
        tk.Button(self.root, text="×", font=("Segoe UI", 12), fg="#888", activeforeground="#ff5f57",
                  command=self.root.quit, padx=0, pady=0, **_btn).place(x=204, y=18, anchor="center")

        # Status label (centred)
        self._lbl_status = tk.Label(self.root, text="FOCUS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR)
        self._lbl_status.place(x=WIN_W // 2, y=18, anchor="center")

        # Drag strip — placed BELOW buttons via .lower() so buttons still get clicks
        drag_strip = tk.Frame(self.root, bg=BG_COLOR, cursor="fleur")
        drag_strip.place(x=0, y=0, width=WIN_W, height=TITLE_H)
        drag_strip.bind("<Button-1>",  self._drag_start)
        drag_strip.bind("<B1-Motion>", self._drag_move)
        drag_strip.lower()

        # Divider below title bar
        tk.Frame(self.root, height=1, bg=DIVIDER_COLOR).pack(fill="x", padx=0, pady=(TITLE_H, 0))

        # Timer display inside a clean background box
        self._timer_canvas = tk.Canvas(self.root, width=160, height=70, bg=BG_COLOR, highlightthickness=0)
        self._timer_canvas.pack(pady=(10, 0))
        draw_timer_box(self._timer_canvas, 160, 70, 12)
        self._timer_text = self._timer_canvas.create_text(80, 35, text="00:00", font=FONT_MAIN, fill="white")

        # Skip button + divider (hidden until active)
        self._btn_skip = RoundedButton(self.root, text="⏭  Skip", command=self.skip_current_period,
                                       width=78, height=24, radius=6, font=("Segoe UI", 8, "bold"),
                                       color="#444345")
        self._skip_divider = tk.Frame(self.root, height=1, bg=DIVIDER_COLOR)

        # Idle hint label
        self._lbl_idle = tk.Label(self.root, text="", font=("Fira Code", 9, "italic"),
                                  fg="#606060", bg=BG_COLOR)

        # Bottom action buttons
        self._btn_frame = tk.Frame(self.root, bg="#000001", height=46)
        self._btn_frame.pack(side="bottom", fill="x")
        self._btn_frame.pack_propagate(False)

        bw, bh, br = WIN_W // 2, 46, 12
        toggle_text = "⏸  Pause" if self.engine.running else "▶  Start"
        self._btn_toggle = RoundedButton(self._btn_frame, text=toggle_text, command=self.toggle_timer,
                                         width=bw, height=bh, radius=br, bg="#000001",
                                         rounded=(False, False, False, True),
                                         border_edges=(True, True, True, True))
        self._btn_toggle.pack(side="left")

        self._btn_reset = RoundedButton(self._btn_frame, text="↺  Reset", command=self.reset_timer,
                                        width=bw, height=bh, radius=br, bg="#000001",
                                        rounded=(False, False, True, False),
                                        border_edges=(True, True, True, False))
        self._btn_reset.pack(side="left")

    def toggle_timer(self) -> None:
        if self.engine.running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self.engine.start()
        if hasattr(self, '_btn_toggle') and self._btn_toggle.winfo_exists():
            self._btn_toggle.update(text="⏸  Pause")
        self._tick()

    def _stop(self) -> None:
        self.engine.stop()
        if hasattr(self, '_btn_toggle') and self._btn_toggle.winfo_exists():
            self._btn_toggle.update(text="▶  Start")
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        if not self._is_mini:
            self._update_skip_visibility()
        else:
            self._refresh_display()

    def reset_timer(self) -> None:
        self._save_session_progress()
        self._stop()
        self.engine.completed_sessions = 0
        self.engine.reset_to_focus()
        self._refresh_display()

    def _tick(self) -> None:
        if not self.engine.running: return
        self.engine.tick()
        if self.engine.running:
            self._timer_id = self.root.after(1000, self._tick)

    def _save_session_progress(self) -> None:
        if self.engine.is_focus:
            elapsed = self.engine.initial_seconds - self.engine.remaining_seconds
            if elapsed > 0:
                self.stats_mgr.record_focus(elapsed)
                self.engine.initial_seconds = self.engine.remaining_seconds

    def _on_period_end(self) -> None:
        self._save_session_progress()
        self._stop()
        if self.engine.is_focus:
            self._handle_focus_end()
        else:
            self._handle_break_end()
        self._refresh_display()

    def _handle_focus_end(self, silent: bool = False) -> None:
        old_f = self.settings.focus_min
        self.engine.transition_to_break()
        
        if silent:
            self._start()
            return

        msg = "Focus session completed. Proceed to your break?"
        if self.settings.focus_min > old_f:
            msg = f"🚀 Focus increased to {self.settings.focus_min}m!\n" + msg
        
        self._show_dialog("Break Time", msg, buttons=[
            {"text": "Start Break", "command": self._start},
            {"text": "Skip", "command": self.skip_break}
        ])

    def _handle_break_end(self, silent: bool = False) -> None:
        self.engine.transition_to_focus()
        if silent:
            self._start()
            return
        self._show_dialog("Break Concluded", "The break period has ended. Resume focus session?", buttons=[
            {"text": "Resume", "command": self._start}
        ])

    def skip_break(self) -> None:
        self.engine.transition_to_focus()
        self._refresh_display()
        self._start()

    def skip_current_period(self) -> None:
        initial = (self.settings.focus_min if self.engine.is_focus else self.settings.break_min) * 60
        if self.engine.running or self.engine.remaining_seconds < initial:
            self._save_session_progress()
            self._stop()
            if self.engine.is_focus:
                self._handle_focus_end(silent=True)
            else:
                self._handle_break_end(silent=True)
            self._refresh_display()

    def _show_dialog(self, title: str, message: str, buttons: list = None, is_error: bool = False) -> None:
        if is_error:
            messagebox.showerror(title, message, parent=self.root)
        else:
            ToastWindow(self.root, title, message, buttons or [])

    def _show_notification(self, title: str, message: str) -> None:
        """Shows a Windows system notification using PowerShell."""
        # Escape single quotes for PowerShell
        safe_msg = message.replace("'", "''")
        safe_title = title.replace("'", "''")
        script = f"""
        [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -id $pid).Path)
        $notification.BalloonTipTitle = '{safe_title}'
        $notification.BalloonTipText = '{safe_msg}'
        $notification.Visible = $True
        $notification.ShowBalloonTip(5000)
        """
        try:
            subprocess.Popen(["powershell", "-Command", script], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

    def _toggle_mini_mode(self) -> None:
        self._is_mini = not self._is_mini
        x, y = self.root.winfo_x(), self.root.winfo_y()
        if self._is_mini:
            w, h = 110, 35
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.bg_canvas.config(width=w, height=h)
            # Re-bind for mini mode
            self.bg_canvas.bind("<Button-1>",        self._on_mini_click)
            self.bg_canvas.bind("<B1-Motion>",       self._drag_move)
            self.bg_canvas.bind("<ButtonRelease-1>", self._on_mini_release)
            self.bg_canvas.bind("<Double-Button-1>", self._on_mini_double_click)
            # Destroy all other widgets
            for child in self.root.winfo_children():
                if child != self.bg_canvas:
                    child.destroy()
        else:
            w, h = WIN_W, WIN_H
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.bg_canvas.config(width=w, height=h)
            self.bg_canvas.unbind("<Double-Button-1>")
            self.bg_canvas.unbind("<Button-1>")
            self.bg_canvas.unbind("<ButtonRelease-1>")
            self.bg_canvas.unbind("<B1-Motion>")
            self.bg_canvas.bind("<Button-1>", self._drag_start)
            self.bg_canvas.bind("<B1-Motion>", self._drag_move)
            draw_rounded_window_bg(self.bg_canvas, w, h, 12, BG_COLOR, OUTLINE_COLOR)
            self._build_ui()
        self._refresh_display()

    def _on_mini_click(self, event) -> None:
        self._drag_start(event)
        self._click_pos = (event.x, event.y)
        self._double_click_pending = False

    def _on_mini_double_click(self, event) -> None:
        if hasattr(self, '_single_click_job'):
            self.root.after_cancel(self._single_click_job)
        self._double_click_pending = True
        self._toggle_mini_mode()

    def _on_mini_release(self, event) -> None:
        if self._double_click_pending:
            return  # Swallow — was a double-click expand, not a single toggle
        if hasattr(self, '_click_pos'):
            dx = abs(event.x - self._click_pos[0])
            dy = abs(event.y - self._click_pos[1])
            if dx < 3 and dy < 3:
                # Use a small delay to allow double-click to cancel this
                self._single_click_job = self.root.after(200, self.toggle_timer)

    def _update_mini_view(self, time_str: str) -> None:
        w, h = 110, 35
        r = 10 
        pct = 0
        if self.engine.initial_seconds > 0:
            elapsed = self.engine.initial_seconds - self.engine.remaining_seconds
            pct = min(elapsed / self.engine.initial_seconds, 1.0)
            
        color = BTN_COLOR if self.engine.is_focus else "#ffb347"
        bg_color = "#1a1a1a"
        self.bg_canvas.delete("all")
        
        # 1. Base Progress/BG layer (Rectangular)
        pw = int(w * pct)
        self.bg_canvas.create_rectangle(0, 0, pw, h, fill=color, outline="")
        self.bg_canvas.create_rectangle(pw, 0, w, h, fill=bg_color, outline="")
        
        # 2. MASK Corners with #000001 (Transparency)
        self._draw_corner_mask(0, 0, r, "tl")
        self._draw_corner_mask(w, 0, r, "tr")
        self._draw_corner_mask(0, h, r, "bl")
        self._draw_corner_mask(w, h, r, "br")
        
        # 3. Outline
        self._draw_outline_only(w, h, r, OUTLINE_COLOR)
        
        # 4. Time
        self.bg_canvas.create_text(w/2, h/2, text=time_str, fill="white", font=("Fira Code", 12, "bold"))

    def _draw_corner_mask(self, x, y, r, corner) -> None:
        """Draw an 'outer' corner mask in transparency color."""
        points = [x, y]
        if corner == "tl":
            points.extend([x+r, y])
            for i in range(90, 181, 10):
                rad = math.radians(i)
                points.extend([x+r + r*math.cos(rad), y+r - r*math.sin(rad)])
            points.extend([x, y+r])
        elif corner == "tr":
            points.extend([x-r, y])
            for i in range(90, -1, -10):
                rad = math.radians(i)
                points.extend([x-r + r*math.cos(rad), y+r - r*math.sin(rad)])
            points.extend([x, y+r])
        elif corner == "bl":
            points.extend([x+r, y])
            for i in range(270, 179, -10):
                rad = math.radians(i)
                points.extend([x+r + r*math.cos(rad), y-r - r*math.sin(rad)])
            points.extend([x, y-r])
        elif corner == "br":
            points.extend([x-r, y])
            for i in range(270, 361, 10):
                rad = math.radians(i)
                points.extend([x-r + r*math.cos(rad), y-r - r*math.sin(rad)])
            points.extend([x, y-r])
        self.bg_canvas.create_polygon(points, fill="#000001", outline="#000001")

    def _draw_outline_only(self, w, h, r, color) -> None:
        """Draw only the rounded border outline."""
        self.bg_canvas.create_arc(0, 0, 2*r-1, 2*r-1, start=90, extent=90, outline=color, style="arc")
        self.bg_canvas.create_arc(w-2*r, 0, w-1, 2*r-1, start=0, extent=90, outline=color, style="arc")
        self.bg_canvas.create_arc(w-2*r, h-2*r, w-1, h-1, start=270, extent=90, outline=color, style="arc")
        self.bg_canvas.create_arc(0, h-2*r, 2*r-1, h-1, start=180, extent=90, outline=color, style="arc")
        self.bg_canvas.create_line(r, 0, w-r, 0, fill=color)
        self.bg_canvas.create_line(r, h-1, w-r, h-1, fill=color)
        self.bg_canvas.create_line(0, r, 0, h-r, fill=color)
        self.bg_canvas.create_line(w-1, r, w-1, h-r, fill=color)

    def _refresh_display(self) -> None:
        mins, secs = divmod(self.engine.remaining_seconds, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        if self._is_mini:
            self._update_mini_view(time_str)
            return

        # Update timer display
        self._timer_canvas.itemconfig(self._timer_text, text=time_str)
        # Ensure text stays on top
        self._timer_canvas.tag_raise(self._timer_text)
        n = self.engine.completed_sessions + 1
        status = f"FOCUS  {n}" if self.engine.is_focus else "BREAK"
        self._lbl_status.config(text=status)
        self._update_skip_visibility()

    def _update_skip_visibility(self) -> None:
        initial = (self.settings.focus_min if self.engine.is_focus else self.settings.break_min) * 60
        # Show skip button if active OR if we're at the start of a period (waiting for user)
        is_active = self.engine.running or self.engine.remaining_seconds <= initial
        if is_active:
            if self._lbl_idle.winfo_ismapped(): self._lbl_idle.pack_forget()
            if not self._btn_skip.winfo_ismapped():
                self._skip_divider.pack(after=self._timer_canvas, fill="x", pady=(10, 0))
                self._btn_skip.pack(after=self._skip_divider, pady=(10, 10))
        else:
            if self._btn_skip.winfo_ismapped():
                self._skip_divider.pack_forget()
                self._btn_skip.pack_forget()
            if not self._lbl_idle.winfo_ismapped():
                self._lbl_idle.config(text="Ready to focus?" if self.engine.is_focus else "Take a breather")
                self._lbl_idle.pack(after=self._timer_canvas, pady=(25, 0))

    def _open_settings(self) -> None: SettingsWindow(self.root, self)
    def _open_stats(self) -> None: StatsWindow(self.root, self)

    def apply_settings(self, **kwargs) -> None:
        self.settings.update(**kwargs)
        if not self.engine.running:
            self.engine.reset_to_focus()
        self._refresh_display()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    PomodoroTimer(root)
    root.mainloop()