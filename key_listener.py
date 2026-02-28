"""
Hotkey detection and state management for Lanite.

Monitors keyboard state and triggers recording start/stop based on
the Ctrl + Space combination. Also handles the kill switch.
"""

import keyboard
import time
import sys
import os
import threading

import speech_engine
import popup

# State variable for tracking activation
active = False

# Kill switch flag
_terminate = False


def terminate():
    """
    Forcefully terminate the application.
    
    Uses os._exit() to immediately kill the process, ensuring
    all threads are stopped regardless of their state.
    This is necessary because Tkinter and daemon threads may
    not respond to sys.exit() properly.
    """
    print("\n" + "=" * 50)
    print("Kill switch triggered (Ctrl + Shift + Space)")
    print("Terminating Lanite...")
    print("=" * 50)
    
    # Gracefully shutdown speech engine
    speech_engine.shutdown()
    
    # Force immediate termination
    # os._exit() kills the entire process including all threads
    os._exit(0)


def monitor():
    """
    Main hotkey monitoring loop.
    
    Polls keyboard state at regular intervals and triggers
    appropriate actions based on key combinations:
    
    - Ctrl + Space (held): Start recording
    - Either key released: Stop recording
    - Ctrl + Shift + Space: Kill switch (terminate application)
    """
    global active, _terminate
    
    while not _terminate:
        # Check for kill switch first (Ctrl + Shift + Space)
        if (keyboard.is_pressed("ctrl") and 
            keyboard.is_pressed("shift") and 
            keyboard.is_pressed("space")):
            _terminate = True
            terminate()
        
        # Check if BOTH Ctrl and Space are currently held down
        # This allows comfortable holding: Ctrl first, then Space
        if keyboard.is_pressed("ctrl") and keyboard.is_pressed("space"):
            if not active:
                active = True
                speech_engine.start()
                popup.show()
        else:
            # If EITHER key is released, stop recording
            if active:
                active = False
                speech_engine.stop()
                popup.hide()
        
        # Polling interval (50Hz)
        time.sleep(0.02)


def run():
    """
    Start the hotkey monitoring loop.
    
    This is a blocking call that runs indefinitely.
    """
    print("Lanite running...")
    print("Press Ctrl + Space to talk.")
    print("Press Ctrl + Shift + Space to exit.")
    print()
    monitor()


def is_active():
    """Return current activation state."""
    return active
