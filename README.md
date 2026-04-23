# 🍅 Adaptive Pomodoro Timer

A professional-grade, professional, and adaptive Pomodoro timer built with Python and Tkinter. This application is designed to help you maintain deep focus by gradually increasing your work sessions and managing your breaks intelligently.

![Pomodoro Timer Preview](https://img.shields.io/badge/Status-Active-brightgreen)
![Python Version](https://img.shields.io/badge/Python-3.x-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## ✨ Features

- **📊 Weekly Focus Stats**: Track your productivity with a built-in visual history of your focus time over the last 7 days.
- **🚀 Adaptive Focus Sessions**: Automatically increases your focus time by a configurable amount after a set number of completed sessions.
- **💡 Intelligent Break Logic**: Break durations automatically scale based on your focus length (5, 10, or 15 minutes) to ensure optimal recovery.
- **🎨 Premium Frameless UI**:
  - Sleek, dark-themed interface with custom rounded buttons.
  - Smooth hover and press animations.
  - Draggable window for flexible placement.
  - "Always on Top" mode to keep your timer visible.
- **⚙️ Persistent Settings**: All your preferences (focus time, break time, increments, etc.) are saved locally in a `config.json` file.
- **🖥️ Taskbar Integration**: Custom Windows integration to ensure the frameless window remains visible and accessible in the taskbar.
- **🔄 Session Management**: Easy start, pause, and reset controls.

## 🛠️ Installation

1. **Prerequisites**: Ensure you have Python 3.x installed on your system.
2. **Clone the Repository**:
   ```bash
   git clone https://github.com/SparshChaurasia/PomodoroApp.git
   cd PomodoroApp
   ```
3. **Run the Application**:
   ```bash
   python pomodoro_timer.py
   ```

*No external dependencies are required beyond the standard Python library (Tkinter).*

## 📖 How to Use

1. **Start Focus**: Click the **▶️ Start** button to begin your focus session.
2. **Manage Sessions**:
   - Use **⏸️ Pause** to take a quick breather.
   - Use **🔄 Reset** to start the current session over.
3. **Adjust Settings**: Click the ⚙️ icon in the top-left corner to open the Settings panel.
4. **Auto-Increment**: After completing the threshold number of sessions (e.g., 5 sessions), the app will notify you and increase your focus time for the next round.

## ⚙️ Configuration

You can tweak the following settings via the UI or by editing `config.json`:

| Setting | Description |
| :--- | :--- |
| **Focus Mins** | Starting duration for focus sessions. |
| **Break Mins** | Starting duration for break sessions. |
| **Inc Amount** | Minutes added to focus time after reaching the threshold. |
| **Sessions/Inc** | Number of sessions required to trigger an increment. |
| **Max Focus** | The upper limit for focus duration increments. |

## 📐 Design Philosophy

This app prioritizes a **distraction-free environment**. The frameless, compact design (220x200) ensures it takes up minimal screen real estate while remaining legible. The use of **Fira Code** ensures a modern, clean look for time and labels.

---

*Developed by Sparsh Chaurasia*
