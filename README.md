<p align="center">
  <img src="lanite/assets/lanite_icon.png" alt="Lanite Logo" width="128" height="128">
</p>

<h1 align="center">Lanite</h1>

<p align="center">
  <strong>Privacy-First Offline Voice Typing Assistant & Dictation Engine for Windows</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#v20-upgrades--comparison">What's New (v2.0)</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#installation--setup">Installation</a> •
  <a href="#usage--hotkeys">Usage</a> •
  <a href="#uiux-showcase">UI/UX Showcase</a> •
  <a href="#project-structure">Project Structure</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/AI--Inference-faster--whisper%20(CTranslate2)-9cf.svg" alt="Inference Engine">
  <img src="https://img.shields.io/badge/VAD-Silero--VAD-orange.svg" alt="VAD Engine">
</p>

---

## Overview

**Lanite** is a native, offline-first voice typing assistant for Windows that brings state-of-the-art AI transcription directly to any application you use. Whether you are coding in VS Code, writing documents in Word, or chatting on Discord, Lanite runs silently in the background and injects your spoken words directly at your cursor.

All transcription is performed 100% locally on your machine. Your voice data never leaves your computer, ensuring complete privacy, zero cloud subscription fees, and zero network dependency.

---

## v2.0 Upgrades & Comparison

This version of Lanite represents a complete structural and features overhaul from its [legacy predecessor](https://github.com/bhaveshmadisetty/lanite). Below is a direct comparison of the architectural and user-experience improvements:

| Dimension | Legacy Version (Predecessor) | Upgraded Version (v2.0) | Benefit / Why It's Better |
| :--- | :--- | :--- | :--- |
| **Global Activation** | `Ctrl + Space` | `Ctrl + Win` (Hold-to-Talk) | **No hotkey conflicts**: The previous shortcut frequently clashed with IDE autocompletions (VS Code, IntelliJ). The new hotkey is conflict-free globally. |
| **Inference Engine** | Vanilla OpenAI Whisper | CTranslate2 (`faster-whisper`) | **4x Faster Transcription**: Dramatically reduces latency and CPU footprint using highly optimized, quantized CTranslate2 weights. |
| **Silence Filtering** | Basic thresholding | Integrated **Silero VAD** | **Zero wasted processing**: Intelligently separates actual speech from silence or background noise, skipping transcription if no speech was detected. |
| **Settings Management** | Manual `config.py` editing | Premium Bento-Style Web Dashboard | **No-code configuration**: Tweak active models, toggles, and view real-time statistics in a modern, interactive UI instead of editing python code. |
| **Visual Feedback** | Static popup status box | Layered click-through Waveform HUD | **OS-Native feel**: A floating, translucent pill HUD renders a real-time voice amplitude visualizer. Focus-isolated (`WS_EX_NOACTIVATE`) so it never steals your cursor. |
| **Running Mode** | Foreground terminal window | Tray Daemon + Silent VBS Launcher | **Stays out of your way**: Runs completely hidden in the system tray. Launcher hides black console prompts (`pythonw.exe`). |
| **Productivity Telemetry** | Local text log file | SQL-Backed Analytics Panel | **Insightful metrics**: Tracks total word count, session times, transcription speeds, and target application dictation frequency. |
| **Formatting Controls** | Basic paste output | Smart space & Filler word removal | **Clean transcriptions**: Strips verbal fillers like "um", "uh", and manages trailing spaces so consecutive sentences connect naturally. |

---

## Key Features

### 🎙️ 100% Offline & Private AI
Transcription operates entirely locally on your CPU or GPU. By employing a localized Whisper model pipeline, your voice recordings never travel across the internet, protecting sensitive documents, credentials, and communications.

### ⚡ Cursor-Level Global Injection
No need to dictate into a standalone app and copy-paste. Lanite hooks directly into the Windows Win32 API to inject text at the current cursor position in any active text input window, from console terminals to web forms.

### 📊 Bento-Style Analytics & Settings Dashboard
An offline web control center built directly into the daemon:
- **Telemetry**: View real-time charts of your dictation speed, total words typed, and session counts.
- **App Tracking**: See which software (e.g., `Code.exe`, `discord.exe`, `chrome.exe`) you dictate into most.
- **Model Selector**: Seamlessly switch between Tiny, Small, and Medium models based on your hardware capabilities.
- **Toggles**: Enable/disable filler word removal, trailing space management, and windows startup tasks with a click.

### 🌊 Reactive Waveform HUD
When holding the activation hotkey, a clean, pill-shaped HUD slides onto your screen:
- **Audio Amplitude**: Renders a 16-bar real-time waveform visualizer reacting to voice levels.
- **State Transition**: Smoothly changes color palette and style when transitioning from "Listening" to "Processing" (thinking).
- **Click-Through**: Uses layered windows transparency (`WS_EX_TRANSPARENT`), allowing you to click elements underneath it.

---

## Installation & Setup

### Prerequisites

* **Windows 10 or 11**
* **Python 3.11+** (validated with Python 3.11 & 3.12)
* **Working microphone**

### Setup Guide

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/bhaveshmadisetty/lanite.git
   cd lanite
   ```

2. **Establish and Activate a Virtual Environment**:
   ```powershell
   python -m venv venv
   # PowerShell
   .\venv\Scripts\Activate.ps1
   # Command Prompt
   .\venv\Scripts\activate.bat
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On your first dictation, Lanite will automatically download and cache the selected Whisper model weights locally.*

---

## Usage & Hotkeys

### Running the Application

* **Developer Mode (Console Output)**:
  Run the entry point inside your activated virtual environment:
  ```bash
  python lanite/main.py
  ```
* **Production Mode (Silent Background)**:
  Simply double-click [Launch Lanite.vbs](file:///d:/Lanite/lanite%20upgraded/Launch%20Lanite.vbs) at the project root. This fires up the engine via `pythonw.exe` (suppressing terminal windows) and mounts the daemon directly into your system tray.

### Hotkeys

| Hotkey | Action | Behavior |
| :--- | :--- | :--- |
| **`Ctrl + Win`** (Hold) | **Start Recording** | Displays the Waveform HUD and begins buffer capture. |
| **`Ctrl + Win`** (Release) | **Transcribe & Inject** | Terminates capture, runs VAD/Whisper, and types text. |
| **`Ctrl + Shift + Win`** | **Emergency Stop** | Global kill-switch that terminates the background process immediately. |

---

## UI/UX Showcase

The upgraded interface components are designed around deep midnight and charcoal visual aesthetics:

### 1. Bento Dashboard (`dashboard.html`)
* Serves as an interactive web page generated by `dashboard.py`.
* Styled in custom dark mode (`#111113`) featuring glassmorphism elements, custom sliders, and live-updating telemetry.
* *Preview Mockup*: Open [obsolete/newdesign.html](file:///d:/Lanite/lanite%20upgraded/obsolete/newdesign.html) in your browser.

### 2. Waveform HUD (`overlay.py`)
* Implemented via a custom Tkinter window using Chroma-key transparency and native Win32 style flags.
* Visualizes real-time mic amplitude without stealing operating system focus.
* *Preview Mockup*: Open [obsolete/newpopup.html](file:///d:/Lanite/lanite%20upgraded/obsolete/newpopup.html) in your browser.

---

## Project Structure

A clean overview of the repository hierarchy:

```
lanite/
├── obsolete/                         # Saved mockups, original notes, and assets
│   ├── newdesign.html                # Settings dashboard mockup
│   ├── newpopup.html                 # Waveform HUD mockup
│   ├── functionalities.txt           # Core technical specifications list
│   ├── promo stuff.txt               # Key promotional notes
│   ├── lanite_icon.ico               # Original icon asset
│   └── lanite_icon.png               # Original logo image
│
├── lanite/                           # Python application source package
│   ├── assets/                       # Active UI templates and icons
│   │   ├── dashboard.html            # UI dashboard served to Edge
│   │   ├── lanite_icon.ico           # Taskbar icon
│   │   └── lanite_icon.png           # Dashboard brand icon
│   ├── audio.py                      # Audio recording & VAD processing loop
│   ├── config.json                   # Saved user configuration parameters
│   ├── dashboard.py                  # HTTP local server & Edge browser bridge
│   ├── history.py                    # SQLite transcription database & telemetry
│   ├── inject.py                     # Win32 keystroke simulation hook
│   ├── lanite.bat                    # CLI launch script
│   ├── main.py                       # Main application daemon
│   ├── overlay.py                    # Floating Tkinter waveform HUD
│   ├── settings.py                   # Local config parser
│   ├── transcribe.py                 # local Whisper translation engine wrapper
│   └── tray.py                       # Windows System Tray daemon
│
├── .gitignore                        # Git exclusion file (ignores virtual env, model caches, logs)
├── Launch Lanite.vbs                 # Silent background script launcher
├── README.md                         # Project documentation
└── requirements.txt                  # Python dependencies manifest
```

---

## Technical Specifications

- **Inference Pipeline**: Quantized CTranslate2 model running `faster-whisper`.
- **Speech Detection**: Silero VAD model (16kHz sample rate).
- **Core APIs**: `pywin32` for window management/keyboard hook listener; `pystray` for Windows tray integration.
- **Graphics Engine**: Tkinter with layered Win32 style settings (`WS_EX_TRANSPARENT`, `WS_EX_NOACTIVATE`) for HUD overlay.

---
*Created by [Bhavesh Madisetty](https://github.com/bhaveshmadisetty)*
