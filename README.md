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

### 🎨 Premium Frameless UI
- **Modern Aesthetics**: Sleek dark-themed interface with neon blue accents.
- **Micro-Animations**: Smooth hover effects and interactive button states.
- **Smart Layout**: A compact, draggable, and "Always on Top" window that stays out of your way but remains accessible.
- **Custom Widgets**: Hand-crafted rounded buttons and specialized UI components built from scratch using Tkinter.

### ⚙️ Intelligent Break Logic
Choose between manual break settings or "Auto" mode, which intelligently scales your recovery time based on the length of your focus session (5, 10, or 15-minute breaks).

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
