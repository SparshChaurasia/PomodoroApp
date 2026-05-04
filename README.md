# 🍅 Adaptive Pomodoro Timer

A professional-grade, adaptive focus companion built with Python. This isn't just a timer; it's a productivity tool designed to grow with your focus span, featuring a sleek frameless UI and built-in analytics.

![App Preview](assets/preview.png)
![App Preview](assets/preview2.png)
![App Preview](assets/preview3.png)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Key Features

### 🚀 Adaptive Focus System
The timer intelligently scales with your productivity. After completing a configurable threshold of sessions, the application automatically increases your focus duration, helping you build deep-work stamina over time.

### 📊 Productivity Analytics
Stay motivated with built-in weekly statistics. Track your daily focus minutes over the last 7 days through a clean, visual bar chart accessible directly within the app.

### ⚙️ Intelligent Break Logic
Choose between manual break settings or "Auto" mode, which dynamically calculates your recovery time based on session intensity:
- **≤ 10m Focus**: 2m break
- **≤ 20m Focus**: 5m break
- **< 60m Focus**: 10m break
- **≥ 60m Focus**: 15m break

### 💊 Mini Mode
A compact, pill-shaped interface for minimal distraction:
- **Real-time Progress**: The background fills as a progress bar.
- **Quick Controls**: Single-click to Start/Pause, Double-click to expand to full view.
- **Window Management**: Perfectly draggable and stays "Always on Top."

### 🎨 Pixel-Perfect Frameless UI
- **Mathematically Precise**: Hand-corrected arc bounding boxes for a perfectly symmetric 1px border.
- **Seamless Design**: Bottom action buttons are integrated into the window frame for a unified look.
- **Modern Iconography**: Clean, high-resolution vector symbols for settings, stats, and window controls.

---

## 🛠️ Installation & Usage

### Running from Source
1. **Prerequisites**: [Python 3.10+](https://www.python.org/downloads/) installed.
2. **Clone the repository**:
   ```bash
   git clone https://github.com/SparshChaurasia/PomodoroApp.git
   cd PomodoroApp
   ```
3. **Launch the app**:
   ```bash
   python main.py
   ```

### 📦 Building the Windows Executable
The application is fully optimized for portability. To create a single-file executable:
1. Install PyInstaller: `pip install pyinstaller`
2. Run the build script:
   ```bash
   PyInstaller --noconsole --onefile --name "PomodoroTimer" --add-data "config.json;." --add-data "stats.csv;." main.py
   ```

---

## ⚙️ Configuration

The app maintains state via `config.json`. You can modify these via the ⚙️ Settings menu or directly in the file:

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `focus_min` | Initial focus session duration (minutes). | 25 |
| `break_min` | Default break duration (if Auto is off). | 5 |
| `break_auto` | Scale break time based on focus length. | `true` |
| `auto_inc_val` | Minutes to add after reaching the session threshold. | 2 |
| `inc_threshold` | Sessions required to trigger an increment. | 5 |
| `max_focus_min` | The hard limit for focus time auto-increments. | 60 |

---

## 📐 Design Philosophy

Built on the principle of **Zero Friction**. 
- No complex setups.
- No external heavy dependencies (Pure Standard Library + Tkinter).
- Lightweight footprint (minimal CPU/RAM usage).
- Data-driven focus (Stats are stored locally in `stats.csv`).

---

### 👤 Author
**Sparsh Chaurasia**
- GitHub: [@SparshChaurasia](https://github.com/SparshChaurasia)

---
