# Usage Guide

## Complete User Manual for Lanite

This guide provides comprehensive instructions for using Lanite's voice dictation capabilities.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Keyboard Controls](#2-keyboard-controls)
3. [Recording Guidelines](#3-recording-guidelines)
4. [Best Practices](#4-best-practices)
5. [Configuration](#5-configuration)
6. [Advanced Features](#6-advanced-features)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start

### Starting Lanite

**Method 1: Command Line**
```cmd
cd C:\Users\YourName\Documents\lanite
.\venv\Scripts\activate
python main.py
```

**Method 2: Desktop Shortcut**
- Double-click the Lanite shortcut on your desktop

### First Run

On first launch, Lanite will:
1. Download the Whisper model (~75 MB for tiny.en)
2. Initialize audio devices
3. Display startup confirmation

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

### Basic Usage

1. Open any text application (Notepad, Word, browser, chat)
2. Place cursor where you want text to appear
3. Hold `Ctrl + Space`
4. Speak clearly
5. Release keys
6. Text appears automatically

---

## 2. Keyboard Controls

### Primary Controls

| Action | Key Combination | Description |
|--------|-----------------|-------------|
| **Start Recording** | Hold `Ctrl + Space` | Begin capturing audio |
| **Stop Recording** | Release either key | End capture, transcribe |
| **Kill Switch** | `Ctrl + Shift + Space` | Terminate application |

### Detailed Behavior

**Starting Recording**:
- Both keys must be pressed (order doesn't matter)
- A popup indicator appears in the bottom-right corner
- A high-pitched beep sounds (if enabled)

**Stopping Recording**:
- Releasing either key stops recording
- A low-pitched beep sounds (if enabled)
- Transcription begins immediately
- Text is pasted automatically

**Kill Switch**:
- Immediately terminates the application
- Use when the application becomes unresponsive
- No cleanup or confirmation prompts

### Key Combination Rationale

The `Ctrl + Space` combination was chosen because:

1. **Natural Hand Position**: Pinky rests on Ctrl, thumb taps Space
2. **Minimal Conflict**: Rare combination in other applications
3. **Comfortable Hold**: Easy to hold while speaking
4. **Quick Release**: Either key stops recording

---

## 3. Recording Guidelines

### Microphone Positioning

| Setup | Recommendation |
|-------|----------------|
| **Built-in laptop mic** | Speak toward the laptop, 30-50 cm away |
| **USB headset** | Position mic to the side of mouth |
| **Desktop microphone** | 15-30 cm from mouth |

### Speaking Tips

**Do**:
- Speak at a natural pace
- Pause briefly between sentences
- Enunciate clearly
- Maintain consistent volume

**Avoid**:
- Speaking too quickly
- Trailing off at sentence ends
- Background noise (TV, music, others talking)
- Covering the microphone

### Audio Feedback

Lanite provides audio cues:

| Sound | Meaning |
|-------|---------|
| High beep (800 Hz) | Recording started |
| Low beep (400 Hz) | Recording stopped |

To disable sounds, edit `config.py`:
```python
# Comment out or remove winsound import
```

---

## 4. Best Practices

### Optimal Recording Length

| Duration | Quality | Use Case |
|----------|---------|----------|
| 1-3 seconds | Excellent | Short phrases, commands |
| 3-10 seconds | Good | Single sentences |
| 10-30 seconds | Moderate | Multiple sentences |
| 30+ seconds | Lower | Long paragraphs |

**Recommendation**: Release keys every 10-15 seconds for best accuracy.

### Application Compatibility

**Fully Compatible**:
- Notepad, Notepad++
- Microsoft Word, Excel
- Web browsers (Chrome, Firefox, Edge)
- Chat applications (Discord, Slack, Teams)
- Email clients

**Partially Compatible**:
- Applications with custom text fields
- Terminal/command prompt (may require paste manually)

**Not Compatible**:
- Applications that block clipboard access
- Applications with hardware-level input blocking

### Punctuation and Formatting

Whisper automatically adds:
- Periods at sentence ends
- Commas for pauses
- Question marks for questions
- Capital letters at sentence starts

**Example**:
```
Spoken: "hello world how are you today"
Output: "Hello world, how are you today?"
```

### Handling Mistakes

If transcription is incorrect:
1. Delete the text manually
2. Re-record the phrase
3. Consider speaking more clearly

For systematic issues:
- Switch to a larger model (base.en)
- Check microphone quality with `check_mic.py`
- Reduce background noise

---

## 5. Configuration

### Accessing Configuration

Edit `config.py` in the project directory:

```python
# config.py - Lanite Configuration
```

### Model Selection

```python
# Options: tiny.en, base.en, small.en
DEFAULT_MODEL = "tiny.en"
```

| Model | Speed | Accuracy | Size |
|-------|-------|----------|------|
| `tiny.en` | Fastest | Good | 75 MB |
| `base.en` | Fast | Excellent | 150 MB |
| `small.en` | Moderate | Best | 500 MB |

### Performance Tuning

```python
# Beam search width (lower = faster)
BEAM_SIZE = 2  # Options: 1, 2, 5

# Compute type for CPU optimization
COMPUTE_TYPE = "int8"  # Options: int8, float16, float32

# Device selection
DEVICE = "cpu"  # Use "cuda" for NVIDIA GPU
```

### UI Customization

```python
# Popup appearance
POPUP_TEXT = "🎤 Listening"  # Custom text
POPUP_FONT = ("Segoe UI", 10)  # Font family, size
POPUP_BG = "black"  # Background color
POPUP_FG = "white"  # Text color
```

### Audio Settings

```python
# Sample rate (should match Whisper's 16kHz)
SAMPLE_RATE = 16000

# Beep frequencies
BEEP_START_FREQ = 800  # Hz
BEEP_STOP_FREQ = 400  # Hz
BEEP_DURATION = 100  # Milliseconds
```

---

## 6. Advanced Features

### History Logging

Lanite can log all transcriptions to a file:

**Location**: `history.txt` in the project directory

**Format**:
```
[2024-01-15 14:30:22] Hello world this is a test.
[2024-01-15 14:31:05] The quick brown fox jumps over the lazy dog.
```

**To disable**: Comment out the logging section in `speech_engine.py`.

### Microphone Diagnostics

Run the diagnostic utility:

```cmd
python check_mic.py
```

**Features**:
- Lists all audio devices
- Shows default microphone details
- Tests recording capability
- Measures audio levels
- Checks sample rate compatibility

### Text Processing

The `text_processor.py` module provides optional cleanup:

```python
from text_processor import process

cleaned = process("um hello world")
# Result: "Hello world."
```

**Available Functions**:
- `remove_fillers()` - Remove "um", "uh", "like"
- `remove_repeated_words()` - Fix "I I think"
- `fix_contractions()` - Expand "I'm" to "I am"
- `smart_punctuation()` - Add appropriate punctuation
- `capitalize_sentences()` - Fix capitalization

### Running Multiple Models

To use different models for different purposes:

1. Create multiple config files:
   - `config_tiny.py`
   - `config_base.py`

2. Modify `speech_engine.py` to import the desired config.

---

## 7. Troubleshooting

### Common Issues and Solutions

#### Issue: No Text Appears

**Possible Causes**:
1. Target application doesn't have focus
2. Clipboard access blocked
3. Keyboard injection blocked

**Solutions**:
1. Click on the target application before recording
2. Check Windows privacy settings for clipboard
3. Try running as Administrator

#### Issue: Text Appears in Wrong Location

**Cause**: Cursor was not positioned before recording.

**Solution**: Click where you want text to appear before holding `Ctrl + Space`.

#### Issue: Incomplete Transcription

**Possible Causes**:
1. Released keys too quickly
2. Speaking too fast
3. Background noise

**Solutions**:
1. Wait 0.5 seconds after speaking before releasing
2. Speak at a moderate pace
3. Reduce background noise

#### Issue: Wrong Words Transcribed

**Possible Causes**:
1. Model doesn't recognize technical terms
2. Accent or pronunciation
3. Poor audio quality

**Solutions**:
1. Switch to `base.en` or `small.en` model
2. Run `check_mic.py` to verify audio quality
3. Use a higher-quality microphone

#### Issue: Application Freezes

**Solutions**:
1. Press `Ctrl + Shift + Space` (kill switch)
2. Check Task Manager for stuck processes
3. Restart application

#### Issue: High CPU Usage

**Solutions**:
1. Use `tiny.en` model
2. Reduce `BEAM_SIZE` to 1
3. Close other CPU-intensive applications

### Diagnostic Commands

```cmd
# Check microphone
python check_mic.py

# Test dependencies
python -c "from faster_whisper import WhisperModel; print('OK')"
python -c "import sounddevice; print('OK')"
python -c "import keyboard; print('OK')"

# Verify FFmpeg
ffmpeg -version
```

---

## 8. Tips and Tricks

### Efficient Dictation Workflow

1. **Position cursor first**: Click where text should appear
2. **Think before speaking**: Plan your sentence
3. **Hold and speak**: Press `Ctrl + Space` and deliver your message
4. **Pause before release**: Wait 0.5 seconds after speaking
5. **Verify**: Check the output and correct if needed

### Performance Optimization

For fastest transcription:
```python
DEFAULT_MODEL = "tiny.en"
BEAM_SIZE = 1
COMPUTE_TYPE = "int8"
```

For best accuracy:
```python
DEFAULT_MODEL = "base.en"  # or small.en
BEAM_SIZE = 5
COMPUTE_TYPE = "float32"
```

### Background Operation

Lanite runs silently in the background:
- No window appears except the small popup
- Works with any application in focus
- Can be minimized to system tray with additional tools

### Keyboard Shortcuts Summary

Print this quick reference:

```
┌─────────────────────────────────────────┐
│          LANITE QUICK REFERENCE         │
├─────────────────────────────────────────┤
│  Ctrl + Space (hold)  → Start recording │
│  Release keys         → Stop & transcribe│
│  Ctrl + Shift + Space → Exit application│
└─────────────────────────────────────────┘
```

---

## 9. FAQ

**Q: Does Lanite work offline?**
A: Yes, completely offline after the initial model download. No internet connection required for transcription.

**Q: Where is my data stored?**
A: All processing happens locally. Audio is never saved. Optional transcription history is stored in `history.txt`.

**Q: Can I change the hotkey?**
A: Yes, modify `key_listener.py` to use different key combinations. See the configuration section.

**Q: Does Lanite support other languages?**
A: Currently optimized for English. Other languages may work with non-English Whisper models.

**Q: How accurate is the transcription?**
A: Accuracy depends on model size and audio quality. `base.en` achieves ~95% accuracy for clear English speech.

**Q: Can I use a GPU?**
A: Yes, set `DEVICE = "cuda"` in `config.py` if you have an NVIDIA GPU with CUDA installed.

---

## Getting Help

For additional support:
1. Check this usage guide
2. Run diagnostics: `python check_mic.py`
3. Review [INSTALLATION.md](INSTALLATION.md)
4. Check [GitHub Issues](https://github.com/bhaveshmadisetty/lanite/issues)
5. Open a new issue with details about your problem
