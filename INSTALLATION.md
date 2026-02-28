# Installation Guide

## Complete Setup Instructions for Windows

This guide provides step-by-step instructions for setting up Lanite on Windows systems. Follow each section carefully to ensure a working installation.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Python Installation](#2-python-installation)
3. [Project Setup](#3-project-setup)
4. [Dependency Installation](#4-dependency-installation)
5. [FFmpeg Setup](#5-ffmpeg-setup)
6. [Verification](#6-verification)
7. [Desktop Shortcut](#7-desktop-shortcut)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Operating System** | Windows 10 | Windows 10/11 |
| **Python** | 3.8 | 3.10+ |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 500 MB | 1 GB |
| **Microphone** | Any USB/analog | Quality USB mic |

### Required Software

- Python 3.8 or higher
- Git (for cloning repository)
- Working microphone with drivers installed

---

## 2. Python Installation

### Step 2.1: Download Python

1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.10 or higher (recommended)
3. Run the installer

### Step 2.2: Installation Options

**Critical**: During installation, check these options:

```
[x] Add Python to PATH
[x] Install pip
[x] Install for all users (optional)
```

### Step 2.3: Verify Installation

Open Command Prompt and run:

```cmd
python --version
```

Expected output:
```
Python 3.10.x
```

If you see an error, Python is not in your PATH. Reinstall with "Add to PATH" checked.

---

## 3. Project Setup

### Step 3.1: Clone Repository

```cmd
# Navigate to your projects folder
cd C:\Users\YourName\Documents

# Clone the repository
git clone https://github.com/bhaveshmadisetty/lanite.git

# Enter project directory
cd lanite
```

### Step 3.2: Create Virtual Environment

```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

After activation, your prompt should show:
```
(venv) C:\Users\YourName\Documents\lanite>
```

### Step 3.3: Verify Virtual Environment

```cmd
# Check Python location
where python
```

Should show:
```
C:\Users\YourName\Documents\lanite\venv\Scripts\python.exe
```

---

## 4. Dependency Installation

### Step 4.1: Install Requirements

```cmd
# Ensure virtual environment is active
.\venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 4.2: Core Dependencies

The following packages will be installed:

| Package | Purpose |
|---------|---------|
| `faster-whisper` | Optimized Whisper inference |
| `sounddevice` | Audio capture via PortAudio |
| `numpy` | Audio data processing |
| `keyboard` | Global hotkey detection |
| `pyperclip` | Clipboard operations |
| `tkinter` | UI (included with Python) |

### Step 4.3: Verify Dependencies

```cmd
# Test faster-whisper installation
python -c "from faster_whisper import WhisperModel; print('OK')"

# Test sounddevice
python -c "import sounddevice; print('OK')"

# Test keyboard
python -c "import keyboard; print('OK')"
```

All commands should output `OK`.

---

## 5. FFmpeg Setup

Whisper requires FFmpeg for audio processing. Lanite supports two setup methods:

### Method A: Project-Local FFmpeg (Recommended)

This method doesn't require modifying system PATH.

1. **Download FFmpeg**:
   - Visit [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - Download Windows builds from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
   - Select "ffmpeg-release-essentials.zip"

2. **Extract FFmpeg**:
   ```cmd
   # Extract the ZIP file
   # Navigate to extracted folder
   cd ffmpeg-*-essentials_build\bin
   ```

3. **Copy to Project**:
   ```cmd
   # Copy ffmpeg.exe to your lanite folder
   copy ffmpeg.exe C:\Users\YourName\Documents\lanite\
   ```

4. **Verify**:
   ```cmd
   cd C:\Users\YourName\Documents\lanite
   .\ffmpeg.exe -version
   ```

### Method B: System PATH (Alternative)

1. Follow steps 1-2 from Method A
2. Add FFmpeg to system PATH:
   - Open "Environment Variables" in Windows Settings
   - Edit "Path" variable
   - Add the path to FFmpeg's bin folder
   - Restart Command Prompt

3. Verify:
   ```cmd
   ffmpeg -version
   ```

---

## 6. Verification

### Step 6.1: Test Audio Hardware

```cmd
python check_mic.py
```

This utility will:
- List all audio devices
- Show default microphone info
- Test recording capability
- Check sample rate compatibility

### Step 6.2: Test Basic Operation

```cmd
python main.py
```

Expected output:
```
==================================================
  Lanite - Offline Voice Dictation Engine
==================================================

Loading Whisper model (tiny.en)...
This may take a moment on first run...
Model loaded successfully!
Lanite running...
Press Ctrl + Space to talk.
Press Ctrl + Shift + Space to exit.
```

### Step 6.3: Test Transcription

1. Open any text editor (Notepad, Word, browser)
2. Hold `Ctrl + Space`
3. Speak clearly: "Hello world"
4. Release keys
5. Text should appear in your active application

### Step 6.4: Test Kill Switch

Press `Ctrl + Shift + Space` to verify the application terminates.

---

## 7. Desktop Shortcut

### Step 7.1: Create Shortcut

```cmd
# Run the shortcut creation script
python create_desktop_shortcut.py
```

This creates a desktop shortcut that:
- Runs Lanite without a console window
- Uses the application icon
- Starts in the correct directory

### Step 7.2: Alternative Manual Shortcut

If the script fails, create a shortcut manually:

1. Right-click on Desktop → New → Shortcut
2. Location: `C:\Users\YourName\Documents\lanite\venv\Scripts\pythonw.exe`
3. Name: `Lanite`
4. Right-click shortcut → Properties
5. Add to Target: ` C:\Users\YourName\Documents\lanite\main.py`
6. Set "Start in": `C:\Users\YourName\Documents\lanite`
7. Change icon: Browse to `lanite_icon.ico`

---

## 8. Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'xxx'"

**Solution**: Install missing package:
```cmd
pip install xxx
```

Or reinstall all dependencies:
```cmd
pip install -r requirements.txt --force-reinstall
```

### Issue: "FFmpeg not found"

**Solution**: Ensure `ffmpeg.exe` is in the project directory:
```cmd
dir ffmpeg.exe
```

If missing, follow [Section 5](#5-ffmpeg-setup).

### Issue: "Keyboard module doesn't detect keys"

**Solution**: Run as Administrator:
1. Right-click Command Prompt
2. Select "Run as administrator"
3. Navigate to project and run

### Issue: "Microphone not detected"

**Solution**:
1. Check Windows Settings → Privacy → Microphone
2. Ensure "Allow apps to access microphone" is ON
3. Run `python check_mic.py` to diagnose

### Issue: "Model download fails"

**Solution**: First run downloads the Whisper model (~75 MB). Ensure:
- Internet connection is active
- No firewall blocking HuggingFace
- Sufficient disk space

### Issue: "Text not pasting"

**Solution**:
1. Ensure target application has focus
2. Check clipboard permissions in Windows Settings
3. Try running as Administrator

### Issue: "Application crashes immediately"

**Solution**:
1. Check if another instance is running:
   ```cmd
   tasklist | findstr python
   ```
2. Kill any running instances:
   ```cmd
   taskkill /F /IM python.exe
   ```
3. Restart application

### Issue: "High CPU usage"

**Solution**: Switch to smaller model in `config.py`:
```python
DEFAULT_MODEL = "tiny.en"  # Fastest
BEAM_SIZE = 1              # Lower = faster
```

---

## 9. Configuration

Edit `config.py` to customize behavior:

```python
# Model selection
DEFAULT_MODEL = "tiny.en"  # tiny.en, base.en, small.en

# Performance tuning
BEAM_SIZE = 2              # Lower = faster, less accurate
COMPUTE_TYPE = "int8"      # Quantization type
DEVICE = "cpu"             # Use "cuda" for NVIDIA GPU

# Audio feedback
BEEP_START_FREQ = 800      # Hz for start sound
BEEP_STOP_FREQ = 400       # Hz for stop sound
BEEP_DURATION = 100        # Milliseconds

# UI settings
POPUP_TEXT = "🎤 Listening"
POPUP_BG = "black"
POPUP_FG = "white"
```

---

## 10. Upgrading

### Update Dependencies

```cmd
# Activate virtual environment
.\venv\Scripts\activate

# Update all packages
pip install -r requirements.txt --upgrade
```

### Update Whisper Model

Larger models provide better accuracy:

```python
# In config.py
DEFAULT_MODEL = "base.en"   # Upgrade from tiny.en
```

First run with new model downloads it automatically.

---

## 11. Uninstallation

### Remove Virtual Environment

```cmd
# Deactivate if active
deactivate

# Delete venv folder
rmdir /s venv
```

### Remove Project

```cmd
cd ..
rmdir /s lanite
```

### Remove Desktop Shortcut

Delete the Lanite shortcut from your desktop.

---

## Getting Help

If you encounter issues not covered in this guide:

1. Run diagnostics: `python check_mic.py`
2. Check [GitHub Issues](https://github.com/bhaveshmadisetty/lanite/issues)
3. Open a new issue with:
   - Windows version
   - Python version (`python --version`)
   - Error message
   - Steps to reproduce
