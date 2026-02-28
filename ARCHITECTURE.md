# Architecture Documentation

## System Design and Technical Decisions

This document provides a comprehensive technical overview of Lanite's architecture, including design decisions, component interactions, and implementation patterns.

---

## 1. High-Level Architecture

### 1.1 System Overview

Lanite implements a multi-threaded, event-driven architecture optimized for real-time audio processing with minimal latency. The system operates on a push-to-talk model where audio is captured only during explicit user activation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LANITE SYSTEM                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│   │   KEYBOARD   │     │    AUDIO     │     │      UI      │        │
│   │    INPUT     │     │    INPUT     │     │   OUTPUT     │        │
│   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘        │
│          │                    │                    │                 │
│          ▼                    ▼                    ▼                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│   │ key_listener │     │speech_engine │     │    popup     │        │
│   │              │     │              │     │              │        │
│   │ • Poll state │     │ • Capture    │     │ • Show/hide  │        │
│   │ • Trigger    │◄───►│ • Transcribe │◄───►│ • Feedback   │        │
│   │ • Kill switch│     │ • Inject     │     │              │        │
│   └──────────────┘     └──────────────┘     └──────────────┘        │
│          │                    │                    │                 │
│          └────────────────────┴────────────────────┘                 │
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │   SHARED STATE    │                            │
│                    │ • listening (bool)│                            │
│                    │ • active (bool)   │                            │
│                    │ • queue (Queue)   │                            │
│                    └───────────────────┘                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

| Principle | Application |
|-----------|-------------|
| **Privacy by Design** | All processing local, no network calls |
| **Minimal Latency** | Optimized inference path, async processing |
| **Thread Isolation** | Clear ownership of resources per thread |
| **Fail-Safe Defaults** | Application exits cleanly on errors |
| **User Control** | Explicit activation, no background listening |

---

## 2. Component Architecture

### 2.1 Main Entry Point (`main.py`)

**Responsibilities**:
- Application initialization
- Single-instance enforcement
- Thread orchestration
- Signal handling

**Design Pattern**: Orchestrator

```python
def main():
    # 1. Acquire single-instance lock (Windows Mutex)
    mutex = acquire_single_instance_lock()
    
    # 2. Initialize speech engine (background thread)
    speech_engine.run()
    
    # 3. Initialize popup UI (main thread required by Tkinter)
    popup_thread = threading.Thread(target=popup.init, daemon=False)
    popup_thread.start()
    
    # 4. Start hotkey listener (blocking)
    key_listener.run()
```

**Single-Instance Implementation**:
```python
def acquire_single_instance_lock():
    mutex_name = "Lanite_Offline_Voice_Dictation_Mutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Lanite is already running. Exiting.")
        sys.exit(0)
    
    return mutex
```

### 2.2 Key Listener (`key_listener.py`)

**Responsibilities**:
- Keyboard state monitoring
- Recording state management
- Kill switch implementation

**Design Pattern**: Observer with Polling

```python
def monitor():
    while not _terminate:
        # Priority 1: Check kill switch
        if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift") and keyboard.is_pressed("space"):
            terminate()
        
        # Priority 2: Check activation
        if keyboard.is_pressed("ctrl") and keyboard.is_pressed("space"):
            if not active:
                active = True
                speech_engine.start()
                popup.show()
        else:
            if active:
                active = False
                speech_engine.stop()
                popup.hide()
        
        time.sleep(0.02)  # 50Hz polling rate
```

**Why Polling vs Hooks**:
- Simpler error handling
- Predictable timing
- No callback registration issues
- Lower system integration complexity

### 2.3 Speech Engine (`speech_engine.py`)

**Responsibilities**:
- Audio stream management
- Whisper model inference
- Text injection via clipboard

**Design Pattern**: Producer-Consumer with Queue

**Architecture Decision**: Always-Open Stream

The critical architectural decision in speech_engine is the always-open stream pattern:

```python
# Stream runs continuously throughout application lifetime
def run():
    # Consumer thread: processes audio when STOP signal received
    threading.Thread(target=audio_loop, daemon=True).start()
    
    # Producer: continuous audio capture
    def start_mic():
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            callback=callback  # Called by PortAudio
        ):
            while not terminate_event.is_set():
                sd.sleep(100)
    
    threading.Thread(target=start_mic, daemon=True).start()
```

**Why Always-Open**:
- Eliminates stream creation/destruction overhead
- Avoids race conditions in stream lifecycle
- Predictable resource usage
- No "cold start" latency on activation

**Audio Queue Pattern**:
```python
q = queue.Queue()
listening = False

def callback(indata, frames, time_info, status):
    """Called by PortAudio on audio thread"""
    if listening:
        q.put(indata.copy())

def audio_loop():
    """Consumer thread"""
    while True:
        audio_chunks = []
        
        # Collect chunks until STOP signal
        while True:
            data = q.get()
            if data == "STOP":
                break
            audio_chunks.append(data)
        
        # Process complete utterance
        full_audio = np.concatenate(audio_chunks)
        segments, _ = model.transcribe(full_audio)
        # ... inject text
```

**Clipboard Injection with Safety Lock**:
```python
# SAFETY LOCK: Wait for physical key release
while keyboard.is_pressed('ctrl') or keyboard.is_pressed('space'):
    time.sleep(0.01)

# Copy to clipboard
pyperclip.copy(final_text)

# VERIFICATION: Wait for clipboard update
timeout = time.time() + 2.0
while pyperclip.paste() != final_text and time.time() < timeout:
    time.sleep(0.01)

# PASTE: Safe to execute
keyboard.send('ctrl+v')
```

### 2.4 Popup UI (`popup.py`)

**Responsibilities**:
- Visual recording indicator
- Thread-safe UI updates

**Design Pattern**: Singleton with Thread-Safe Access

**Tkinter Threading Rules**:
- Tkinter operations MUST occur on the thread that created the Tk instance
- Background threads CANNOT directly call Tkinter methods
- `root.after(0, callback)` schedules callbacks on the main thread

```python
_root = None  # Module-level singleton

def init():
    """MUST be called from main thread"""
    global _root
    _root = tk.Tk()
    _root.overrideredirect(True)  # No window decorations
    _root.attributes("-topmost", True)
    # ... setup UI
    _root.withdraw()  # Start hidden
    _root.mainloop()  # Blocking

def show():
    """Can be called from any thread"""
    if _root:
        _root.after(0, _root.deiconify)  # Schedule on main thread

def hide():
    """Can be called from any thread"""
    if _root:
        _root.after(0, _root.withdraw)
```

### 2.5 Configuration (`config.py`)

**Responsibilities**:
- Centralized constants
- User-customizable settings

**Design Pattern**: Configuration Object

```python
# Audio Configuration
SAMPLE_RATE = 16000  # Whisper native rate

# Model Configuration
DEFAULT_MODEL = "tiny.en"  # Options: tiny.en, base.en, small.en

# Performance Tuning
BEAM_SIZE = 2          # Transcription beam width
COMPUTE_TYPE = "int8"  # Quantization for CPU

# UI Configuration
POPUP_TEXT = "🎤 Listening"
POPUP_BG = "black"
```

---

## 3. Data Flow

### 3.1 Recording Flow

```
User holds Ctrl+Space
         │
         ▼
┌─────────────────┐
│ key_listener    │
│ active = True   │
└────────┬────────┘
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌─────────────────┐      ┌─────────────────┐
│ speech_engine   │      │     popup       │
│ listening=True  │      │     show()      │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Audio Callback  │
│ queue.put(data) │◄─── PortAudio callback
└─────────────────┘
         │
         ▼
Audio chunks accumulate in queue
```

### 3.2 Transcription Flow

```
User releases keys
         │
         ▼
┌─────────────────┐
│ key_listener    │
│ active = False  │
└────────┬────────┘
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌─────────────────┐      ┌─────────────────┐
│ speech_engine   │      │     popup       │
│ queue.put(STOP) │      │     hide()      │
│ listening=False │      └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   audio_loop    │
│ receives STOP   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Concatenate     │
│ audio chunks    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ model.transcribe│
│ (Whisper)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Safety Lock     │
│ Wait for keys   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Clipboard       │
│ copy + verify   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ keyboard.send   │
│ Ctrl+V          │
└─────────────────┘
```

---

## 4. Threading Model

### 4.1 Thread Responsibilities

| Thread | Function | Responsibilities |
|--------|----------|------------------|
| Main | `popup.init()` | Tkinter event loop, UI rendering |
| Background 1 | `key_listener.monitor()` | Keyboard state polling |
| Background 2 | `speech_engine.audio_loop()` | Audio processing, transcription |
| Background 3 | `speech_engine.start_mic()` | Audio stream management |
| Audio Callback | PortAudio thread | Queue audio data |

### 4.2 Thread Synchronization

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNCHRONIZATION POINTS                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                    ┌─────────────┐          │
│  │key_listener │ ──── active ────►  │   popup     │          │
│  │   thread    │                    │   (main)    │          │
│  └─────────────┘                    └─────────────┘          │
│         │                                  ▲                 │
│         │ listening                        │ after(0)        │
│         ▼                                  │                 │
│  ┌─────────────┐                    ┌─────────────┐          │
│  │speech_engine│ ◄─── queue ─────── │audio_callback│          │
│  │audio_loop   │                    │  (PortAudio)│          │
│  └─────────────┘                    └─────────────┘          │
│                                                              │
│  State Variables (shared):                                   │
│  • listening: bool (speech_engine → callback)                │
│  • active: bool (key_listener → speech_engine)               │
│  • queue: Queue (callback → audio_loop)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Thread Safety Mechanisms

| Mechanism | Purpose | Implementation |
|-----------|---------|----------------|
| `queue.Queue` | Thread-safe audio data transfer | Built-in thread-safe queue |
| `threading.Event` | Graceful shutdown signaling | `terminate_event.is_set()` |
| `root.after(0, ...)` | Thread-safe UI updates | Tkinter main thread scheduling |
| Global boolean flags | Simple state sharing | Atomic read/write in Python |

---

## 5. Model Integration

### 5.1 Whisper Architecture

Lanite uses `faster-whisper`, a CTranslate2-optimized implementation of OpenAI's Whisper model:

```
┌─────────────────────────────────────────────────────────────┐
│                    WHISPER INFERENCE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input Audio (16kHz, mono, float32)                          │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────┐                                         │
│  │   Log-Mel       │  80-dimension mel spectrogram          │
│  │   Spectrogram   │  30-second windows                     │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │   Encoder       │  Transformer encoder layers            │
│  │   (Frozen)      │  int8 quantization                     │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                         │
│  │   Decoder       │  Autoregressive token generation       │
│  │                 │  Beam search (beam_size=2)             │
│  └────────┬────────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  Output: text segments with timestamps                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Model Selection Trade-offs

| Model | Size | Latency | Memory | Accuracy | Use Case |
|-------|------|---------|--------|----------|----------|
| tiny.en | 75 MB | 0.5s | 200 MB | Good | Real-time chat |
| base.en | 150 MB | 1.0s | 350 MB | Excellent | General dictation |
| small.en | 500 MB | 2.0s | 600 MB | Best | Professional use |

### 5.3 Optimization Techniques

```python
model = WhisperModel(
    "tiny.en",
    device="cpu",        # CPU inference (no GPU dependency)
    compute_type="int8"  # INT8 quantization for speed
)

segments, info = model.transcribe(
    audio,
    beam_size=2,         # Reduced beam for speed
    language="en"        # Skip language detection
)
```

---

## 6. Error Handling Strategy

### 6.1 Error Categories

| Category | Handling | Example |
|----------|----------|---------|
| **Startup Errors** | Exit with message | Model not found |
| **Runtime Errors** | Log and continue | Transcription failure |
| **Fatal Errors** | Clean shutdown | Unhandled exception |

### 6.2 Graceful Degradation

```python
# Audio feedback optional
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False  # Continue without audio feedback

# History logging optional
try:
    with open("history.txt", "a") as f:
        f.write(transcription)
except Exception:
    pass  # Continue without logging
```

### 6.3 Cleanup on Exit

```python
def terminate():
    """Kill switch handler"""
    speech_engine.shutdown()  # Signal stream to close
    time.sleep(0.2)           # Allow cleanup
    os._exit(0)               # Force termination
```

---

## 7. Performance Considerations

### 7.1 Latency Budget

| Stage | Time (tiny.en) | Time (base.en) |
|-------|----------------|----------------|
| Audio capture | 0 ms | 0 ms |
| Chunk concatenation | ~5 ms | ~5 ms |
| Whisper inference | ~500 ms | ~1000 ms |
| Clipboard update | ~20 ms | ~20 ms |
| Paste operation | ~10 ms | ~10 ms |
| **Total** | **~535 ms** | **~1035 ms** |

### 7.2 Memory Footprint

| Component | Memory Usage |
|-----------|--------------|
| Python interpreter | ~30 MB |
| Whisper model (tiny.en) | ~75 MB |
| Model runtime | ~100 MB |
| Audio buffers | ~1 MB |
| UI (Tkinter) | ~5 MB |
| **Total** | **~200 MB** |

### 7.3 CPU Utilization

- **Idle**: <1% (thread sleeping)
- **Recording**: <5% (audio callback only)
- **Transcribing**: 10-30% (single core, 1-2 seconds)

---

## 8. Security Considerations

### 8.1 Privacy by Design

| Aspect | Implementation |
|--------|----------------|
| No cloud dependency | All processing local |
| No telemetry | Zero network calls |
| No logging by default | Optional history file |
| User-controlled activation | Push-to-talk only |

### 8.2 System Integration Risks

| Risk | Mitigation |
|------|------------|
| Keystroke injection | Safety lock before typing |
| Clipboard manipulation | Verification before paste |
| Always-on microphone | Push-to-talk activation |

---

## 9. Future Architecture Considerations

### 9.1 Potential Improvements

| Area | Current | Proposed |
|------|---------|----------|
| State management | Global flags | State machine class |
| Event system | Direct calls | Observer pattern |
| Configuration | Python file | JSON/YAML + UI |
| Logging | Print statements | Structured logging |
| Model switching | Manual code edit | Runtime selection |

### 9.2 Extensibility Points

- **Plugin system**: Custom text processors
- **Hotkey customization**: User-defined combinations
- **Model hotswap**: Change models without restart
- **Output formats**: Markdown, code formatting

---

## 10. Conclusion

Lanite's architecture reflects iterative refinement through real-world usage. The always-open stream pattern, while initially counterintuitive, proved to be the most stable solution for real-time audio processing. Thread isolation with clear ownership boundaries enables predictable behavior and easier debugging.

The architecture prioritizes:
1. **Stability** over feature completeness
2. **User control** over automation
3. **Privacy** over convenience
4. **Simplicity** over optimization

These priorities result in a system that is reliable, maintainable, and trustworthy for daily use.
