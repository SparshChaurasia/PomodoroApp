import tkinter as tk
from tkinter import messagebox
import ctypes
import os
import sys
import winsound
import json
import csv
from datetime import datetime, timedelta

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
STATS_NAME  = "stats.csv"

DEFAULTS = {
    "focus_min":    25,
    "break_min":    5,
    "break_auto":   True,
    "auto_inc_val": 2,
    "inc_threshold": 5,
    "max_focus_min": 60,
}

# ── UI Constants ───────────────────────────────────────────────────────────────
DIALOG_WIDTH  = 260
DIALOG_HEIGHT = 300

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

class StatsManager:
    """Handles daily focus time tracking."""
    def __init__(self, filename: str):
        self.path = get_app_path(filename)
        self.stats = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) == 2:
                            self.stats[row[0]] = int(row[1])
            except (OSError, ValueError):
                pass

    def record_focus(self, seconds: int):
        if seconds <= 0: return
        today = str(datetime.now().date())
        self.stats[today] = self.stats.get(today, 0) + seconds
        self.save()

    def save(self):
        try:
            with open(self.path, "w", newline='') as f:
                writer = csv.writer(f)
                for date, secs in self.stats.items():
                    writer.writerow([date, secs])
        except OSError:
            pass

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
    if focus_min < 30:
        return 5
    if focus_min <= 60:
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
    canvas.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, outline=outline, style="arc")
    canvas.create_arc(w-2*r, 0, w-1, 2*r, start=0, extent=90, outline=outline, style="arc")
    canvas.create_arc(w-2*r, h-2*r, w-1, h-1, start=270, extent=90, outline=outline, style="arc")
    canvas.create_arc(0, h-2*r, 2*r, h-1, start=180, extent=90, outline=outline, style="arc")
    
    canvas.create_line(r, 0, w-r, 0, fill=outline)
    canvas.create_line(r, h-1, w-r, h-1, fill=outline)
    canvas.create_line(0, r, 0, h-r, fill=outline)
    canvas.create_line(w-1, r, w-1, h-r, fill=outline)


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
        outline_color = "#aaaaaa"
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
            self.create_arc(0, 0, r*2, r*2, start=90, extent=90, outline=outline_color, style="arc")
        if top_right and border_top and border_right:
            self.create_arc(w-r*2, 0, w-1, r*2, start=0, extent=90, outline=outline_color, style="arc")
        if bot_right and border_bottom and border_right:
            self.create_arc(w-r*2, h-r*2, w-1, h-1, start=270, extent=90, outline=outline_color, style="arc")
        if bot_left and border_bottom and border_left:
            self.create_arc(0, h-r*2, r*2, h-1, start=180, extent=90, outline=outline_color, style="arc")

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
        super().__init__(parent, DIALOG_WIDTH, DIALOG_HEIGHT)
        self._timer = timer
        self._build_ui()

    def _build_ui(self) -> None:
        t = self._timer

        # Title and Close button
        tk.Label(self, text="SETTINGS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR
                 ).place(x=DIALOG_WIDTH//2, y=18, anchor="center")
        
        tk.Button(self, text="❌", font=FONT_CLOSE, command=self.destroy, bg=BG_COLOR, fg="white", bd=0
                  ).place(x=DIALOG_WIDTH - 20, y=18, anchor="center")

        # Top horizontal divider
        tk.Frame(self, height=1, bg="#444444").pack(fill="x", padx=0, pady=(35, 0))

        # Rows with 10px top padding for the first element to match timer spacing
        self._f  = self._make_row("Focus", t.settings.focus_min, first=True)
        
        # Break row with Auto checkbox
        self._break_auto_var = tk.BooleanVar(value=t.settings.data.get("break_auto", True))
        self._b, self._b_chk = self._make_row_with_auto("Break", t.settings.break_min, self._break_auto_var)
        
        self._a  = self._make_row("Increment By", t.settings.auto_inc_val)
        self._th = self._make_row("Increment Every", t.settings.inc_threshold)
        self._mf = self._make_row("Max Focus", t.settings.max_focus_min)

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
                break_min    = int(self._b.get()) if not self._break_auto_var.get() else self._timer.settings.break_min,
                break_auto   = self._break_auto_var.get(),
                auto_inc_val = int(self._a.get()),
                inc_threshold= int(self._th.get()),
                max_focus_min= int(self._mf.get()),
            )
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number!", parent=self)


# ── Stats window ───────────────────────────────────────────────────────────────
class StatsWindow(DraggableWindow):
    """A frameless, draggable Toplevel for viewing weekly focus history."""

    def __init__(self, parent: tk.Misc, stats: dict):
        super().__init__(parent, DIALOG_WIDTH, DIALOG_HEIGHT)
        self._stats = stats
        self._build_ui()

    def _build_ui(self) -> None:
        # Title and Close button
        tk.Label(self, text="STATS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR
                 ).place(x=DIALOG_WIDTH//2, y=18, anchor="center")
        
        tk.Button(self, text="❌", font=FONT_CLOSE, command=self.destroy, bg=BG_COLOR, fg="white", bd=0
                  ).place(x=DIALOG_WIDTH - 20, y=18, anchor="center")

        # Top horizontal divider
        tk.Frame(self, height=1, bg="#444444").pack(fill="x", padx=0, pady=(35, 0))

        # Container for bars
        container = tk.Frame(self, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Get last 7 days
        today = datetime.now().date()
        days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        
        max_val = max([self._stats.get(str(d), 0) for d in days] + [3600]) # Minimum scale of 1 hour

        for d in days:
            d_str = str(d)
            val = self._stats.get(d_str, 0)
            day_name = d.strftime("%a %d/%m")
            
            row = tk.Frame(container, bg=BG_COLOR)
            row.pack(fill="x", pady=2)
            
            tk.Label(row, text=day_name, font=FONT_LABEL, fg="#aaa", bg=BG_COLOR, width=10, anchor="w").pack(side="left")
            
            # Progress bar simulation
            bar_bg = tk.Frame(row, bg="#444345", height=12)
            bar_bg.pack(side="left", fill="x", expand=True, padx=(5, 10))
            
            pct = min(val / max_val, 1.0)
            if val > 0:
                tk.Frame(bar_bg, bg=BTN_COLOR, width=int(pct * 120), height=12).place(x=0, y=0)
            
            tk.Label(row, text=f"{val//60}m", font=FONT_LABEL, fg="white", bg=BG_COLOR, width=4).pack(side="right")


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

        self._configure_window()
        self._build_ui()
        self._refresh_display()

    def _configure_window(self) -> None:
        self.root.title("Pomodoro")
        w, h = 220, 230
        self.root.geometry(f"{w}x{h}")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        self.root.config(bg="#000001")
        self.root.wm_attributes("-transparentcolor", "#000001")

        self.bg_canvas = tk.Canvas(self.root, width=w, height=h, bg="#000001", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)
        draw_rounded_window_bg(self.bg_canvas, w, h, 12, BG_COLOR, "#aaaaaa")

        show_in_taskbar(self.root)
        self.bg_canvas.bind("<Button-1>", self._drag_start)
        self.bg_canvas.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event) -> None:
        self._drag_x, self._drag_y = event.x, event.y

    def _drag_move(self, event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        # Adjusted Y to 18 and added anchor="center" for all top bar items to ensure perfect middle alignment
        tk.Button(self.root, text="⚙️", font=FONT_CLOSE, command=self._open_settings, bg=BG_COLOR, fg="white", bd=0
                  ).place(x=15, y=18, anchor="center")
        tk.Button(self.root, text="📊", font=FONT_CLOSE, command=self._open_stats, bg=BG_COLOR, fg="white", bd=0
                  ).place(x=40, y=18, anchor="center")
        tk.Button(self.root, text="❌", font=FONT_CLOSE, command=self.root.quit, bg=BG_COLOR, fg="white", bd=0
                  ).place(x=206, y=18, anchor="center")

        self._lbl_status = tk.Label(self.root, text="FOCUS", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR)
        self._lbl_status.place(x=110, y=18, anchor="center")

        tk.Frame(self.root, height=1, bg="#444444").pack(fill="x", padx=0, pady=(35, 0))

        self._lbl_time = tk.Label(self.root, text="00:00", font=FONT_MAIN, fg="white", bg=BG_COLOR)
        self._lbl_time.pack(pady=(10, 0))

        self._btn_skip = RoundedButton(self.root, text="⏭ Skip", command=self.skip_current_period,
                                       width=70, height=22, radius=6, font=("Fira Code", 9, "bold"), color=BG_COLOR)
        self._skip_divider = tk.Frame(self.root, height=1, bg="#444444")

        self._lbl_idle = tk.Label(self.root, text="", font=("Fira Code", 10, "italic"), fg="#777777", bg=BG_COLOR)
        
        tk.Frame(self.root, height=1, bg="#444444").pack(side="bottom", fill="x")
        self._btn_frame = tk.Frame(self.root, bg="#000001", height=45)
        self._btn_frame.pack(side="bottom", fill="x")
        self._btn_frame.pack_propagate(False)

        bw, bh, br = 110, 45, 12
        self._btn_toggle = RoundedButton(self._btn_frame, text="▶ Start", command=self.toggle_timer,
                                         width=bw, height=bh, radius=br, bg="#000001",
                                         rounded=(False, False, False, True), border_edges=(True, True, True, True))
        self._btn_toggle.pack(side="left")

        self._btn_reset = RoundedButton(self._btn_frame, text="🔄 Reset", command=self.reset_timer,
                                        width=bw, height=bh, radius=br, bg="#000001",
                                        rounded=(False, False, True, False), border_edges=(True, True, True, False))
        self._btn_reset.pack(side="left")

    def toggle_timer(self) -> None:
        if self.engine.running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self.engine.start()
        self._btn_toggle.update(text="⏸️ Pause")
        self._tick()

    def _stop(self) -> None:
        self.engine.stop()
        self._btn_toggle.update(text="▶ Start")
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None
        self._update_skip_visibility()

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

        info = []
        if self.settings.focus_min > old_f:
            info.append(f"🚀 Focus increased to {self.settings.focus_min}m!")
        
        msg = "\n".join(info + ["Session complete!", f"Take a {self.settings.break_min} min break."])
        buttons = [{"text": "Start Break", "command": self._start}, {"text": "Skip Break", "command": self.skip_break}]
        self._show_dialog("Break Time", msg, buttons=buttons)

    def _handle_break_end(self, silent: bool = False) -> None:
        self.engine.transition_to_focus()
        if silent:
            self._start()
            return
        buttons = [{"text": "Start Focus", "command": self._start}, {"text": "End Session", "command": self.reset_timer}]
        self._show_dialog("Back to Work", "Break over! Time to focus.", buttons=buttons)

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
        width_pad = " " * 60
        padded_msg = f"{width_pad}\n{message}\n{width_pad}"
        try:
            winsound.MessageBeep(winsound.MB_ICONHAND if is_error else winsound.MB_ICONASTERISK)
        except Exception: pass

        if buttons and len(buttons) >= 2:
            prompt = f"{padded_msg}\n\nDo you want to {buttons[0]['text']}?"
            if messagebox.askyesno(title, prompt, parent=self.root):
                if buttons[0]["command"]: buttons[0]["command"]()
            else:
                if buttons[1]["command"]: buttons[1]["command"]()
        else:
            func = messagebox.showerror if is_error else messagebox.showinfo
            func(title, padded_msg, parent=self.root)

    def _refresh_display(self) -> None:
        mins, secs = divmod(self.engine.remaining_seconds, 60)
        self._lbl_time.config(text=f"{mins:02d}:{secs:02d}")
        status = f"FOCUS ({self.engine.completed_sessions + 1})" if self.engine.is_focus else "BREAK"
        self._lbl_status.config(text=status)
        self._update_skip_visibility()

    def _update_skip_visibility(self) -> None:
        initial = (self.settings.focus_min if self.engine.is_focus else self.settings.break_min) * 60
        is_active = self.engine.running or self.engine.remaining_seconds < initial
        if is_active:
            if self._lbl_idle.winfo_ismapped(): self._lbl_idle.pack_forget()
            if not self._btn_skip.winfo_ismapped():
                self._skip_divider.pack(after=self._lbl_time, fill="x", pady=(10, 0))
                self._btn_skip.pack(after=self._skip_divider, pady=(10, 10))
        else:
            if self._btn_skip.winfo_ismapped():
                self._skip_divider.pack_forget()
                self._btn_skip.pack_forget()
            if not self._lbl_idle.winfo_ismapped():
                self._lbl_idle.config(text="Ready to focus?" if self.engine.is_focus else "Take a breather")
                self._lbl_idle.pack(after=self._lbl_time, pady=(25, 0))

    def _open_settings(self) -> None: SettingsWindow(self.root, self)
    def _open_stats(self) -> None: StatsWindow(self.root, self.stats_mgr.stats)

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