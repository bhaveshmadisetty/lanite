# Changelog

All notable changes to Lanite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- GPU inference support (CUDA)
- Configuration UI
- Multi-language support
- Streaming transcription display

---

## [1.0.0] - 2026-02-28

### Added

#### Core Features
- **Offline Voice Dictation**: Complete offline speech-to-text using Whisper
- **Push-to-Talk Activation**: `Ctrl + Space` hotkey for recording control
- **Visual Indicator**: Tkinter popup showing recording status
- **Kill Switch**: `Ctrl + Shift + Space` for immediate termination
- **Single Instance Lock**: Windows Mutex prevents multiple instances

#### Speech Engine
- **Whisper Integration**: faster-whisper for optimized CPU inference
- **Model Selection**: Support for tiny.en, base.en, and small.en models
- **INT8 Quantization**: CPU-optimized inference with int8 compute type
- **Audio Feedback**: Configurable start/stop beep sounds

#### Text Processing
- **Automatic Punctuation**: Whisper's context-aware punctuation
- **Grammar Cleanup Module**: Optional post-processing utilities
  - Filler word removal
  - Consecutive duplicate removal
  - Contraction expansion
  - Smart punctuation insertion
  - Sentence capitalization

#### User Experience
- **Clipboard Injection**: Text pasted instantly via clipboard
- **Safety Lock**: Prevents OS shortcut conflicts during typing
- **Verification Loop**: Ensures clipboard updates before pasting
- **History Logging**: Optional transcription history file

#### Utilities
- **Microphone Diagnostics**: `check_mic.py` for audio troubleshooting
- **Desktop Shortcut Creator**: `create_desktop_shortcut.py` for easy access
- **Configuration File**: Centralized settings in `config.py`

### Architecture

#### Threading Model
- Main thread: Tkinter event loop for popup UI
- Background thread 1: Keyboard state monitoring
- Background thread 2: Audio processing loop
- Background thread 3: Microphone stream management

#### Design Patterns
- Producer-Consumer pattern for audio queue
- Singleton pattern for Whisper model
- Observer pattern for keyboard polling

### Performance

| Metric | tiny.en | base.en |
|--------|---------|---------|
| Model Size | ~75 MB | ~150 MB |
| RAM Usage | ~200 MB | ~350 MB |
| Latency (3s audio) | ~0.5s | ~1.0s |

### Dependencies
- faster-whisper >= 0.10.0
- sounddevice >= 0.4.6
- numpy >= 1.24.0
- keyboard >= 0.13.5
- pyperclip >= 1.8.2

---

## Development History

### Phase 1: Initial Prototype (Vosk Era)

#### [0.1.0] - Development
- Initial Vosk-based speech recognition
- Basic hotkey detection with keyboard library
- PyAutoGUI for simulated typing

#### [0.2.0] - Development
- PartialResult implementation for real-time feedback
- Duplicate text prevention with state tracking

### Phase 2: Architecture Refinement

#### [0.3.0] - Development
- Migration to always-open stream pattern
- Thread isolation improvements
- State lifecycle stabilization

#### [0.4.0] - Development
- Single Ctrl hotkey replaced with Ctrl+Space
- Kill switch implementation
- Restart bug fixes

### Phase 3: Engine Migration

#### [0.5.0] - Development
- Migration from Vosk to Whisper
- faster-whisper integration
- Clipboard injection replacing simulated typing

#### [0.6.0] - Development
- Safety lock for key release detection
- Clipboard verification loop
- Race condition prevention

### Phase 4: Polish and Stability

#### [0.7.0] - Development
- Text processor module for grammar cleanup
- Audio feedback with winsound
- History logging feature

#### [0.8.0] - Development
- Popup UI with Tkinter
- Thread-safe UI updates via `after()`
- Bottom-right corner positioning

#### [0.9.0] - Development
- Single instance lock with Windows Mutex
- Desktop shortcut generator
- Microphone diagnostic utility

#### [0.9.5] - Release Candidate
- Configuration file system
- Documentation completion
- Bug fixes and stability improvements

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | Dev | Vosk prototype |
| 0.2.0 | Dev | Real-time feedback |
| 0.3.0 | Dev | Stream architecture |
| 0.4.0 | Dev | Hotkey redesign |
| 0.5.0 | Dev | Whisper migration |
| 0.6.0 | Dev | Clipboard injection |
| 0.7.0 | Dev | Text processing |
| 0.8.0 | Dev | Popup UI |
| 0.9.0 | Dev | Utilities |
| 0.9.5 | RC | Release candidate |
| 1.0.0 | 2026-02-28 | Initial release |

---

## Upgrade Guide

### From Development Builds

If you've been using development builds:

1. Backup your `config.py` if customized
2. Pull latest changes: `git pull origin main`
3. Reinstall dependencies: `pip install -r requirements.txt --upgrade`
4. Verify model: Delete cached model to download latest version
5. Test: `python main.py`

### Configuration Changes

Version 1.0.0 introduces a centralized `config.py`. If you have custom settings:

1. Compare your settings with the new `config.py`
2. Migrate any custom values
3. New options available:
   - `BEAM_SIZE` for transcription quality
   - `COMPUTE_TYPE` for optimization
   - `DEVICE` for GPU support

---

## Breaking Changes

### From Vosk to Whisper

The migration from Vosk to Whisper introduced these changes:

| Aspect | Vosk (Old) | Whisper (New) |
|--------|------------|---------------|
| Processing | Streaming | Batch |
| Punctuation | Manual | Automatic |
| Context | None | Full sentence |
| Model Size | ~50 MB | ~75-500 MB |
| Latency | Lower | Higher |

### Hotkey Change

- **Old**: Single Ctrl key
- **New**: Ctrl + Space combination

This change prevents accidental activation during normal computer use.

---

## Known Issues

### Current Limitations

1. **Windows Only**: Currently supports Windows only
2. **No Streaming Display**: Text appears after recording stops
3. **Fixed Language**: English-only optimization
4. **Manual Model Selection**: Requires config file edit

### Workarounds

- **Language Support**: Use non-English Whisper models with manual configuration
- **Model Selection**: Create multiple config files for different models

---

## Migration Path

### Future Versions

Planned changes for future releases:

- **v1.1.0**: Configuration UI, model hotswap
- **v1.2.0**: GPU support, performance improvements
- **v2.0.0**: Multi-language, streaming display

---

[Unreleased]: https://github.com/bhaveshmadisetty/lanite/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/bhaveshmadisetty/lanite/releases/tag/v1.0.0
