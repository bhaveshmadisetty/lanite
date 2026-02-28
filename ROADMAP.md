# Roadmap

## Future Development Plans for Lanite

This document outlines the planned development trajectory for Lanite, including upcoming features, improvements, and long-term vision.

---

## Version Timeline

```
2026 Q1          Q2              Q3              Q4
   │              │               │               │
   ▼              ▼               ▼               ▼
┌──────┐      ┌──────┐       ┌──────┐       ┌──────┐
│ v1.0 │ ───► │ v1.1 │ ───►  │ v1.2 │ ───►  │ v2.0 │
│ Core │      │  UI  │       │ GPU  │       │ Multi│
│ Stable│     │Config│       │ Speed│       │feature│
└──────┘      └──────┘       └──────┘       └──────┘
```

---

## Short-Term Goals (v1.1)

### Target: Q2 2026

#### Configuration UI

**Objective**: Replace config.py editing with graphical settings

**Features**:
- System tray icon with settings menu
- Model selection dropdown
- Hotkey customization
- Audio device selection
- Performance tuning sliders

**Technical Approach**:
```
┌─────────────────────────────────────┐
│         Lanite Settings             │
├─────────────────────────────────────┤
│ Model: [tiny.en ▼]                  │
│                                     │
│ Hotkey: [Ctrl + Space    ] [Change] │
│                                     │
│ Audio Device: [Default Mic ▼]       │
│                                     │
│ Performance:                        │
│ Speed ○──────●──────○ Accuracy      │
│                                     │
│ [ ] Start with Windows              │
│ [x] Show popup indicator            │
│ [x] Play audio feedback             │
│                                     │
│           [Save] [Cancel]           │
└─────────────────────────────────────┘
```

**Files Modified**:
- New: `settings_ui.py`
- Modified: `main.py`, `config.py`

---

#### Model Hotswap

**Objective**: Change models without restart

**Implementation**:
- Model download manager
- Runtime model switching
- Model cache management
- Progress indicators

**Technical Details**:
```python
class ModelManager:
    def __init__(self):
        self.available_models = ["tiny.en", "base.en", "small.en"]
        self.current_model = None
        self.cache_dir = Path.home() / ".lanite" / "models"
    
    def download_model(self, model_name: str) -> bool:
        """Download model with progress callback."""
        pass
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to different model at runtime."""
        pass
```

---

#### System Tray Integration

**Objective**: Minimize to tray with status indicator

**Features**:
- Tray icon with recording status
- Right-click menu for quick actions
- Status tooltips
- Notification for transcription complete

**Libraries**:
- `pystray` for system tray
- `PIL` for icon generation

---

## Medium-Term Goals (v1.2)

### Target: Q3 2026

#### GPU Acceleration

**Objective**: Support CUDA for faster transcription

**Requirements**:
- NVIDIA GPU with CUDA support
- PyTorch with CUDA
- Modified inference pipeline

**Performance Targets**:

| Model | CPU Latency | GPU Latency | Improvement |
|-------|-------------|-------------|-------------|
| tiny.en | 0.5s | 0.2s | 2.5x |
| base.en | 1.0s | 0.4s | 2.5x |
| small.en | 2.0s | 0.6s | 3.3x |

**Implementation**:
```python
def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

model = WhisperModel(
    model_name,
    device=get_device(),
    compute_type="float16" if get_device() == "cuda" else "int8"
)
```

---

#### Streaming Transcription

**Objective**: Display text in real-time during speech

**Approach**: Hybrid Vosk + Whisper pipeline

```
┌─────────────────────────────────────┐
│      STREAMING ARCHITECTURE         │
├─────────────────────────────────────┤
│                                      │
│  Audio Input                         │
│      │                               │
│      ▼                               │
│  ┌───────────┐    ┌───────────┐      │
│  │   Vosk    │───►│  Display  │      │
│  │ Streaming │    │ (Realtime)│      │
│  └───────────┘    └───────────┘      │
│      │                               │
│      ▼ (on release)                  │
│  ┌───────────┐    ┌───────────┐      │
│  │  Whisper  │───►│  Replace  │      │
│  │  Batch    │    │ (Final)   │      │
│  └───────────┘    └───────────┘      │
│                                      │
└─────────────────────────────────────┘
```

**Benefits**:
- Immediate visual feedback
- Placeholder text while processing
- Final accurate transcription

---

#### Performance Optimization

**Objective**: Reduce latency and resource usage

**Strategies**:
1. **Audio Buffer Optimization**
   - Dynamic buffer sizing
   - Silence pre-filtering
   - Compression for memory efficiency

2. **Inference Optimization**
   - ONNX Runtime integration
   - Quantization improvements
   - Batch processing for multiple utterances

3. **Memory Management**
   - Model unloading when inactive
   - Garbage collection tuning
   - Memory-mapped audio buffers

---

## Long-Term Goals (v2.0)

### Target: Q4 2026

#### Multi-Language Support

**Objective**: Support multiple languages with automatic detection

**Features**:
- Language auto-detection
- Per-language model management
- Code-switching support
- Language-specific punctuation rules

**Model Requirements**:
- tiny (multilingual): ~75 MB
- base (multilingual): ~150 MB
- Language packs for offline use

---

#### Advanced Text Processing

**Objective**: Intelligent post-processing pipeline

**Features**:

1. **Context-Aware Correction**
   - Learn from user corrections
   - Domain-specific vocabularies
   - Custom dictionary support

2. **Formatting Modes**
   - Plain text
   - Markdown
   - Code comments
   - Email formatting

3. **Command Integration**
   - Voice commands for formatting
   - "New paragraph", "comma", "period"
   - Custom command macros

---

#### Cloud Sync (Optional)

**Objective**: Optional cloud features for users who want them

**Features**:
- Settings sync across devices
- Custom dictionary sync
- Usage analytics (opt-in)
- Model download acceleration

**Privacy Guarantee**:
- All core features remain offline
- Cloud features explicitly opt-in
- No voice data uploaded
- End-to-end encryption for sync

---

## Feature Request Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Configuration UI | High | Medium | P1 |
| GPU Support | High | Medium | P1 |
| System Tray | Medium | Low | P2 |
| Streaming Display | High | High | P2 |
| Multi-Language | High | Medium | P3 |
| Voice Commands | Medium | Medium | P3 |
| Cloud Sync | Low | High | P4 |
| Mobile Companion | Low | High | P4 |

---

## Technical Debt

### Current Issues to Address

| Issue | Impact | Effort | Target Version |
|-------|--------|--------|----------------|
| Global state variables | Maintainability | Medium | v1.1 |
| No formal state machine | Reliability | Medium | v1.1 |
| Print-based logging | Debugging | Low | v1.1 |
| No unit tests | Quality | High | v1.2 |
| Hardcoded paths | Portability | Low | v1.1 |

### Planned Refactoring

1. **State Management**
   - Implement proper state machine
   - Centralize state in dedicated module
   - Add state transition logging

2. **Error Handling**
   - Structured exception hierarchy
   - Graceful degradation patterns
   - User-friendly error messages

3. **Testing Infrastructure**
   - Unit tests for core modules
   - Integration tests for workflows
   - Performance benchmarks

---

## Community Involvement

### Areas for Contribution

| Area | Difficulty | Guidance |
|------|------------|----------|
| Documentation | Easy | Full guidance available |
| Bug fixes | Medium | Reproducible issues prioritized |
| UI components | Medium | Design specs provided |
| Performance | Hard | Profiling data available |
| New features | Hard | Architecture discussion required |

### Good First Issues

Look for issues labeled:
- `good first issue` - Suitable for newcomers
- `documentation` - Documentation improvements
- `help wanted` - Community assistance needed

---

## Release Schedule

### Versioning Strategy

- **Major (X.0)**: Breaking changes, major features
- **Minor (1.X)**: New features, backward compatible
- **Patch (1.0.X)**: Bug fixes, minor improvements

### Release Cadence

| Type | Frequency | Content |
|------|-----------|---------|
| Major | Quarterly | Significant new features |
| Minor | Monthly | Feature additions |
| Patch | As needed | Bug fixes |

---

## Success Metrics

### Technical Metrics

| Metric | Current | Target (v1.2) |
|--------|---------|---------------|
| Latency (tiny.en) | 0.5s | 0.3s |
| Memory usage | 200 MB | 150 MB |
| CPU usage (idle) | <1% | <0.5% |
| Startup time | 3s | 1s |

### User Experience Metrics

| Metric | Current | Target (v2.0) |
|--------|---------|---------------|
| Setup steps | 5 | 2 |
| Configuration options | 8 | 15 |
| Supported languages | 1 | 10+ |
| Platform support | Windows | Windows, Linux, macOS |

---

## Long-Term Vision

### 3-Year Goals

1. **Platform Expansion**
   - macOS support
   - Linux support
   - Potential mobile companion app

2. **Enterprise Features**
   - Team dictionaries
   - Corporate vocabularies
   - HIPAA-compliant mode

3. **Integration Ecosystem**
   - VS Code extension
   - Browser extension
   - API for third-party apps

4. **AI Advancements**
   - Real-time translation
   - Speaker diarization
   - Emotion detection

---

## Feedback and Suggestions

We value community input on our roadmap. To provide feedback:

1. **Feature Requests**: Open an issue with `feature request` label
2. **Roadmap Discussion**: Use GitHub Discussions
3. **Priority Voting**: React to issues with 👍

---

*This roadmap is subject to change based on community feedback, technical constraints, and resource availability.*
