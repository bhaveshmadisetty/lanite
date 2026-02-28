"""
Configuration constants for Lanite.

Modify these values to customize application behavior.
"""

# Audio Configuration
SAMPLE_RATE = 16000  # Whisper expects 16kHz audio

# Model Configuration
# Options: tiny.en, base.en, small.en, medium.en, large
# tiny.en:  ~75MB, fastest, good accuracy
# base.en:  ~150MB, fast, excellent accuracy
# small.en: ~500MB, moderate, best accuracy
DEFAULT_MODEL = "tiny.en"

# UI Configuration
POPUP_TEXT = "🎤 Listening"
POPUP_FONT = ("Segoe UI", 10)
POPUP_BG = "black"
POPUP_FG = "white"

# Audio Feedback Frequencies (Hz)
BEEP_START_FREQ = 800  # High beep when recording starts
BEEP_STOP_FREQ = 400   # Low beep when recording stops
BEEP_DURATION = 100    # Duration in milliseconds

# Threading Configuration
HOTKEY_POLL_INTERVAL = 0.02  # Seconds between key state checks (50Hz)

# Clipboard Configuration
CLIPBOARD_TIMEOUT = 2.0  # Max seconds to wait for clipboard update

# Whisper Configuration
BEAM_SIZE = 2  # Lower = faster, slightly less accurate
COMPUTE_TYPE = "int8"  # Quantization for CPU efficiency
DEVICE = "cpu"  # Use "cuda" for GPU acceleration
