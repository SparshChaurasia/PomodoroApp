import tkinter as tk
from tkinter import messagebox
import ctypes
import os
import json
import csv
from datetime import datetime, timedelta

# ── Constants ──────────────────────────────────────────────────────────────────
BG_COLOR    = "#333235"
BTN_COLOR   = "#4cc2ff"
FONT_MAIN   = ("Fira Code", 35, "bold")
FONT_BTN    = ("Fira Code", 11, "bold")
FONT_LABEL  = ("Fira Code", 10)
FONT_CLOSE  = ("Fira Code", 8)
CONFIG_NAME = "config.json"
STATS_NAME  = "stats.csv"

# ── UI Constants ───────────────────────────────────────────────────────────────
DIALOG_WIDTH  = 260
DIALOG_HEIGHT = 300

DEFAULTS = {
    "focus_min":    25,
    "break_min":    5,
    "auto_inc_val": 2,
    "inc_threshold": 5,
    "max_focus_min": 60,
}


# ── Helpers ────────────────────────────────────────────────────────────────────
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
    
    # Border (1px White)
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


        self._draw(self._color)
        self.bind("<Button-1>",        lambda _: self._draw(self.PRESS_COLOR))
        self.bind("<ButtonRelease-1>", lambda _: self._on_release())
        self.bind("<Enter>",           lambda _: self._draw(self.HOVER_COLOR))
        self.bind("<Leave>",           lambda _: self._draw(self._color))

    def _draw(self, color: str) -> None:
        self.delete("all")
        w, h, r = self._btn_w, self._btn_h, self._radius

        # Rounded rect via four corner ovals + two fill rectangles
        for x0, y0, x1, y1 in [
            (0, 0, r*2, r*2), (w-r*2, 0, w, r*2),
            (0, h-r*2, r*2, h), (w-r*2, h-r*2, w, h),
        ]:
            self.create_oval(x0, y0, x1, y1, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        self.create_text(w/2, h/2, text=self._text, fill="white", font=self._font)

    def _on_release(self) -> None:
        self._draw(self._color)
        if self._command:
            self._command()

    def update(self, text: str = None, color: str = None) -> None:
        """Update label text and/or background colour and redraw."""
        if text  is not None: self._text  = text
        if color is not None: self._color = color
        self._draw(self._color)


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

        # Close button
        tk.Button(
            self, text="❌", font=FONT_CLOSE,
            command=self.destroy, bg=BG_COLOR, fg="white", bd=0,
        ).place(x=DIALOG_WIDTH - 25, y=10)

        # Top spacer
        tk.Frame(self, bg=BG_COLOR, height=40).pack()

        self._f  = self._make_row("Focus Mins",    t.focus_min)
        self._b  = self._make_row("Break Mins",    t.break_min)
        self._a  = self._make_row("Inc Amount",    t.auto_inc_val)
        self._th = self._make_row("Sessions/Inc",  t.inc_threshold)
        self._mf = self._make_row("Max Focus",     t.max_focus_min)

        RoundedButton(self, text="💾 Save", command=self._save,
                      color=BTN_COLOR, width=DIALOG_WIDTH - 40).pack(pady=15)

    def _make_row(self, label: str, value) -> tk.Entry:
        row = tk.Frame(self, bg=BG_COLOR)
        row.pack(fill="x", padx=20, pady=5)
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
                break_min    = int(self._b.get()),
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
        # Close button
        tk.Button(
            self, text="❌", font=FONT_CLOSE,
            command=self.destroy, bg=BG_COLOR, fg="white", bd=0,
        ).place(x=DIALOG_WIDTH - 25, y=10)

        tk.Label(self, text="Weekly Stats", font=FONT_BTN, fg=BTN_COLOR, bg=BG_COLOR).pack(pady=(30, 10))

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
    """Adaptive Pomodoro timer with persistent settings and auto-increment."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._timer_id: str | None = None

        self._configure_window()
        self._load_settings()
        self._load_stats()
        self._init_state()
        self._build_ui()

    # ── Window setup ──────────────────────────────────────────────────────────
    def _configure_window(self) -> None:
        self.root.title("Pomodoro")
        w, h = 220, 200
        self.root.geometry(f"{w}x{h}")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        # Rounded corners setup
        self.root.config(bg="#000001")
        self.root.wm_attributes("-transparentcolor", "#000001")

        self.bg_canvas = tk.Canvas(self.root, width=w, height=h, bg="#000001", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)
        draw_rounded_window_bg(self.bg_canvas, w, h, 12, BG_COLOR, "#aaaaaa")

        show_in_taskbar(self.root)
        
        # Bindings for dragging
        self.bg_canvas.bind("<Button-1>", self._drag_start)
        self.bg_canvas.bind("<B1-Motion>", self._drag_move)
        self.root.bind("<Button-1>",  self._drag_start)
        self.root.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event) -> None:
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    # ── State ─────────────────────────────────────────────────────────────────
    def _init_state(self) -> None:
        self.timer_running          = False
        self.is_focus_period        = True
        self.completed_sessions     = 0
        self.remaining_seconds      = self.focus_min * 60
        self._initial_seconds       = self.remaining_seconds

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # Settings button (top left)
        tk.Button(
            self.root, text="⚙️", font=FONT_CLOSE,
            command=self._open_settings, bg=BG_COLOR, fg="white", bd=0,
        ).place(x=8, y=8)

        # Stats button (next to settings)
        tk.Button(
            self.root, text="📊", font=FONT_CLOSE,
            command=self._open_stats, bg=BG_COLOR, fg="white", bd=0,
        ).place(x=32, y=8)

        # Close button (top right)
        tk.Button(
            self.root, text="❌", font=FONT_CLOSE,
            command=self.root.quit, bg=BG_COLOR, fg="white", bd=0,
        ).place(x=195, y=8)

        self._lbl_time = tk.Label(
            self.root, text=self._format_time(),
            font=FONT_MAIN, fg="white", bg=BG_COLOR,
        )
        self._lbl_time.pack(pady=(40, 20))

        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.pack(fill="x", padx=10, pady=10)

        self._btn_toggle = RoundedButton(frame, text="▶ Start", command=self.toggle_timer, width=96)
        self._btn_toggle.pack(side="left", expand=True, padx=2)

        RoundedButton(frame, text="🔄 Reset", command=self.reset_timer, width=96).pack(side="left", expand=True, padx=2)

    # ── Timer control ─────────────────────────────────────────────────────────
    def toggle_timer(self) -> None:
        if self.timer_running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self.timer_running = True
        self._btn_toggle.update(text="⏸️ Pause")
        self._tick()

    def _stop(self) -> None:
        self.timer_running = False
        self._btn_toggle.update(text="▶ Start")
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def reset_timer(self) -> None:
        self._save_session_progress()
        self._stop()
        self.remaining_seconds = self.focus_min * 60
        self._initial_seconds  = self.remaining_seconds
        self.is_focus_period   = True
        self._refresh_display()

    def _tick(self) -> None:
        if not self.timer_running:
            return
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._refresh_display()
            self._timer_id = self.root.after(1000, self._tick)
        else:
            self._on_period_end()

    def _save_session_progress(self) -> None:
        """Record focused time since last save point."""
        if self.is_focus_period:
            elapsed = self._initial_seconds - self.remaining_seconds
            if elapsed > 0:
                self._record_focus(elapsed)
                self._initial_seconds = self.remaining_seconds

    def _on_period_end(self) -> None:
        self._save_session_progress()
        self._stop()
        if self.is_focus_period:
            self._handle_focus_end()
        else:
            self._handle_break_end()
        self._refresh_display()

    def _handle_focus_end(self) -> None:
        self.completed_sessions += 1

        focus_increased = False
        info_lines = []
        if self.completed_sessions % self.inc_threshold == 0:
            if self.focus_min < self.max_focus_min:
                self.focus_min = min(self.focus_min + self.auto_inc_val, self.max_focus_min)
                info_lines.append(f"🚀 Focus increased to {self.focus_min}m!")
                focus_increased = True
            else:
                info_lines.append("⭐ Max focus level reached!")

        # Only auto-scale break if focus has increased; otherwise respect manual setting
        if focus_increased:
            self.break_min = compute_break(self.focus_min)

        self.is_focus_period    = False
        self.remaining_seconds  = self.break_min * 60
        self._initial_seconds   = self.remaining_seconds
        
        msg = "\n".join(info_lines + ["Session complete!", f"Take a {self.break_min} min break."])
        
        buttons = [
            {"text": "Start Break", "command": self._start},
            {"text": "Skip Break",  "command": self.skip_break}
        ]
        self._show_dialog("Break Time", msg, buttons=buttons)

    def _handle_break_end(self) -> None:
        self.is_focus_period   = True
        self.remaining_seconds = self.focus_min * 60
        self._initial_seconds  = self.remaining_seconds
        
        buttons = [
            {"text": "Start Focus", "command": self._start},
            {"text": "End Session", "command": self.reset_timer}
        ]
        self._show_dialog("Back to Work", "Break over! Time to focus.", buttons=buttons)

    def skip_break(self) -> None:
        """Immediately start next focus session."""
        self.is_focus_period = True
        self.remaining_seconds = self.focus_min * 60
        self._initial_seconds  = self.remaining_seconds
        self._refresh_display()
        self._start()

    def _show_dialog(self, title: str, message: str, buttons: list = None, is_error: bool = False) -> None:
        """Use the system default native messagebox for notifications."""
        if buttons and len(buttons) >= 2:
            # Map native Yes/No to the first two button actions
            prompt = f"{message}\n\nDo you want to {buttons[0]['text']}?"
            if messagebox.askyesno(title, prompt, parent=self.root):
                if buttons[0]["command"]: buttons[0]["command"]()
            else:
                if buttons[1]["command"]: buttons[1]["command"]()
        else:
            if is_error:
                messagebox.showerror(title, message, parent=self.root)
            else:
                messagebox.showinfo(title, message, parent=self.root)

    # ── Display ───────────────────────────────────────────────────────────────
    def _format_time(self) -> str:
        mins, secs = divmod(self.remaining_seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def _refresh_display(self) -> None:
        self._lbl_time.config(text=self._format_time())

    # ── Settings ──────────────────────────────────────────────────────────────
    @property
    def _config_path(self) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)

    def _load_settings(self) -> None:
        data = {}
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        for key, default in DEFAULTS.items():
            setattr(self, key, data.get(key, default))

    def _save_settings(self) -> None:
        payload = {k: getattr(self, k) for k in DEFAULTS}
        try:
            with open(self._config_path, "w") as f:
                json.dump(payload, f, indent=4)
        except OSError as e:
            self._show_dialog("Save Error", str(e), is_error=True)

    def apply_settings(self, **kwargs) -> None:
        """Called by SettingsWindow after the user hits Save."""
        for key, val in kwargs.items():
            setattr(self, key, val)
        self._save_settings()
        if not self.timer_running:
            self.remaining_seconds = self.focus_min * 60
            self._initial_seconds  = self.remaining_seconds
        self._refresh_display()

    def _open_settings(self) -> None:
        SettingsWindow(self.root, self)

    # ── Stats ─────────────────────────────────────────────────────────────────
    @property
    def _stats_path(self) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), STATS_NAME)

    def _load_stats(self) -> None:
        self.stats = {}
        if os.path.exists(self._stats_path):
            try:
                with open(self._stats_path, newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) == 2:
                            self.stats[row[0]] = int(row[1])
            except (OSError, ValueError):
                pass

    def _record_focus(self, seconds: int) -> None:
        today = str(datetime.now().date())
        self.stats[today] = self.stats.get(today, 0) + seconds
        try:
            with open(self._stats_path, "w", newline='') as f:
                writer = csv.writer(f)
                for date, secs in self.stats.items():
                    writer.writerow([date, secs])
        except OSError:
            pass

    def _open_stats(self) -> None:
        StatsWindow(self.root, self.stats)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    PomodoroTimer(root)
    root.mainloop()