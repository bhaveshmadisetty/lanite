#!/usr/bin/env python3
"""
Lanite - Offline Push-to-Talk AI Voice Engine

A privacy-first, offline voice dictation system for Windows.
Uses Whisper for speech recognition with instant clipboard injection.

Usage:
    python main.py

Controls:
    Ctrl + Space (hold)    - Start recording
    Release keys           - Stop recording and transcribe
    Ctrl + Shift + Space   - Kill switch (terminate application)
"""

import threading
import sys
import os
import ctypes


def acquire_single_instance_lock():
    """
    Acquires a named Windows Mutex to ensure only one instance of Lanite runs.
    """
    mutex_name = "Lanite_Offline_Voice_Dictation_Mutex"
    kernel32 = ctypes.windll.kernel32
    # CreateMutexW returns a handle to the mutex object
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    # 183 is ERROR_ALREADY_EXISTS
    if last_error == 183:
        print("Lanite is already running. Exiting.")
        sys.exit(0)
        
    return mutex  # Keep reference so it isn't garbage collected

# Enforce single instance immediately before heavy imports
_global_mutex = acquire_single_instance_lock()

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import key_listener
import speech_engine
import popup


def main():
    """
    Initialize and run Lanite.
    
    The application runs multiple threads:
    - Main thread: Tkinter popup UI (via popup.init())
    - Background: Audio capture, Whisper processing, hotkey detection
    """
    print("=" * 50)
    print("  Lanite - Offline Voice Dictation Engine")
    print("=" * 50)
    print()
    
    # Start audio engine in background thread
    # This initializes Whisper model and starts mic stream
    speech_engine.run()
    
    # Start popup UI on main thread (required by Tkinter)
    # This also handles the main event loop
    popup_thread = threading.Thread(
        target=popup.init,
        daemon=False  # Must be non-daemon for Tkinter
    )
    popup_thread.start()
    
    # Start hotkey listener (blocking)
    # This runs indefinitely until kill switch is triggered
    key_listener.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nLanite terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
