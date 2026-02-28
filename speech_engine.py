"""
Speech recognition engine for Lanite.

Handles audio capture, Whisper model inference, and text injection.
Uses a queue-based architecture for thread-safe audio processing.

Architecture:
    - Audio stream runs continuously in callback mode
    - Audio data is queued when 'listening' flag is True
    - STOP signal triggers batch processing by Whisper
    - Text is injected via clipboard with verification
"""

import queue
import sounddevice as sd
import threading
import numpy as np
import os
import time
import keyboard
import pyperclip
import sys

# Platform-specific imports
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

from faster_whisper import WhisperModel

# --- LAZY PATH FIX ---
# Add current directory to PATH for FFmpeg detection
# This allows FFmpeg to be placed in the project directory
os.environ["PATH"] += os.pathsep + os.getcwd()

# Configuration
SAMPLE_RATE = 16000  # Whisper native sample rate
BEAM_SIZE = 2        # Transcription beam width

# Audio queue for thread communication
q = queue.Queue()

# State flag for recording
listening = False

# Event for graceful shutdown
terminate_event = threading.Event()

# --- MODEL INITIALIZATION ---
print("Loading Whisper model (tiny.en)...")
print("This may take a moment on first run...")
try:
    model = WhisperModel(
        "tiny.en",
        device="cpu",
        compute_type="int8"
    )
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure you have an internet connection for first-time model download.")
    sys.exit(1)


def play_status_sound(freq):
    """
    Play a beep sound to indicate status change.
    
    Args:
        freq: Frequency in Hz (800 = start, 400 = stop)
    """
    if HAS_WINSOUND:
        threading.Thread(
            target=winsound.Beep,
            args=(freq, 100),
            daemon=True
        ).start()


def callback(indata, frames, time_info, status):
    """
    Audio stream callback function.
    
    Called by sounddevice when audio data is available.
    Only queues data when listening flag is True.
    
    Args:
        indata: Audio data buffer (numpy array)
        frames: Number of frames
        time_info: Timing information
        status: Status flags
    """
    if listening:
        q.put(indata.copy())


def audio_loop():
    """
    Main audio processing loop.
    
    Waits for STOP signal, then:
    1. Concatenates all queued audio chunks
    2. Runs Whisper transcription
    3. Injects text via clipboard
    
    Runs in a background daemon thread.
    """
    while True:
        audio_chunks = []
        
        # Collect audio chunks until STOP signal
        while True:
            data = q.get()
            if isinstance(data, str) and data == "STOP":
                break
            audio_chunks.append(data)
        
        # Skip if no audio was captured
        if not audio_chunks:
            continue
        
        print("⏹️ Processing audio...")
        
        try:
            # Concatenate all audio chunks into single buffer
            full_audio = np.concatenate(audio_chunks, axis=0).flatten().astype(np.float32)
            
            # Run Whisper transcription
            segments, _ = model.transcribe(full_audio, beam_size=BEAM_SIZE)
            
            # Extract text from segments
            final_text = " ".join([
                segment.text.strip()
                for segment in segments
                if segment.text.strip()
            ])
            
            if final_text:
                # Add trailing space for continuous typing
                final_text = final_text + " "
                print(f"Heard: {final_text}")
                
                # Append to history log
                try:
                    history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.txt")
                    with open(history_path, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {final_text.strip()}\n")
                except Exception as log_e:
                    print(f"Failed to log history: {log_e}")
                
                # === SAFETY LOCK ===
                # Wait until user has physically released ALL keys
                # This prevents OS shortcut conflicts
                while keyboard.is_pressed('ctrl') or keyboard.is_pressed('space'):
                    time.sleep(0.01)
                
                # === CLIPBOARD INJECTION ===
                # Copy text to clipboard
                pyperclip.copy(final_text)
                
                # === VERIFICATION LOOP ===
                # Wait for Windows to actually update the clipboard
                # This prevents race conditions where paste happens
                # before clipboard is updated
                timeout = time.time() + 2.0
                while pyperclip.paste() != final_text and time.time() < timeout:
                    time.sleep(0.01)
                
                # === PASTE OPERATION ===
                # Now safe to paste the verified text
                keyboard.send('ctrl+v')
                
                print("✅ Pasted text.")
            else:
                print("⚠️ No speech detected.")
                
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}\n")


def start():
    """
    Start recording audio.
    
    Sets the listening flag and plays start sound.
    Called by key_listener when hotkey is pressed.
    """
    global listening
    listening = True
    play_status_sound(800)
    print("🎤 Listening...")


def stop():
    """
    Stop recording audio.
    
    Clears the listening flag, sends STOP signal to audio loop,
    and plays stop sound. Called by key_listener when hotkey is released.
    """
    global listening
    if listening:
        listening = False
        q.put("STOP")
        play_status_sound(400)


def shutdown():
    """
    Gracefully shutdown the audio stream so the microphone is released properly.
    """
    terminate_event.set()
    # Give the stream a moment to close
    time.sleep(0.2)


def run():
    """
    Initialize and start the speech engine.
    
    Spawns two background threads:
    1. Audio processing loop (collects chunks, runs Whisper)
    2. Microphone stream (captures audio via callback)
    """
    # Start audio processing loop
    threading.Thread(target=audio_loop, daemon=True).start()
    
    # Start microphone stream
    def start_mic():
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=callback
        ):
            # Keep stream alive until terminate signal
            while not terminate_event.is_set():
                sd.sleep(100)
    
    threading.Thread(target=start_mic, daemon=True).start()
