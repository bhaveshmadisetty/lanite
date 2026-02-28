# Security Policy

## Security Overview for Lanite

This document outlines the security considerations, policies, and procedures for Lanite - an offline voice dictation application.

---

## Table of Contents

1. [Security Philosophy](#1-security-philosophy)
2. [Privacy by Design](#2-privacy-by-design)
3. [Data Handling](#3-data-handling)
4. [Security Features](#4-security-features)
5. [Known Vulnerabilities](#5-known-vulnerabilities)
6. [Reporting Security Issues](#6-reporting-security-issues)
7. [Security Updates](#7-security-updates)

---

## 1. Security Philosophy

### Core Principles

Lanite is built on the principle that your voice data is among your most sensitive information. Unlike text, voice contains biometric markers, emotional state, and contextual clues that should never leave your control.

**Our Security Principles**:

| Principle | Implementation |
|-----------|----------------|
| **Local-First Processing** | All computation happens on your device |
| **Zero Network Dependency** | No internet required after model download |
| **No Telemetry** | We collect zero usage data |
| **Explicit User Control** | Recording only when explicitly activated |
| **Minimal Attack Surface** | No network services, no APIs, no servers |

### Threat Model

Lanite is designed to protect against:

| Threat | Mitigation |
|--------|------------|
| Data interception | No network transmission |
| Cloud breaches | No cloud storage |
| Unauthorized recording | Push-to-talk activation |
| Memory scraping | Process isolation |
| Supply chain attacks | Pinned dependencies |

---

## 2. Privacy by Design

### Data Flow Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANITE DATA FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                                                │
│  │ Microphone  │                                                │
│  │   Hardware  │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────┐      ┌─────────────┐                           │
│  │   Audio     │ ───► │   Memory    │ (RAM only, never disk)    │
│  │   Buffer    │      │   Buffer    │                           │
│  └─────────────┘      └──────┬──────┘                           │
│                              │                                   │
│                              ▼                                   │
│                       ┌─────────────┐                           │
│                       │   Whisper   │ (Local inference)         │
│                       │   Model     │                           │
│                       └──────┬──────┘                           │
│                              │                                   │
│                              ▼                                   │
│                       ┌─────────────┐                           │
│                       │   Text      │                           │
│                       │   Output    │                           │
│                       └──────┬──────┘                           │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│       ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│       │ Clipboard│    │ History  │    │ Screen   │             │
│       │ (memory) │    │ (optional│    │ (target  │             │
│       │          │    │  file)   │    │  app)    │             │
│       └──────────┘    └──────────┘    └──────────┘             │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  NETWORK BOUNDARY: ZERO DATA CROSSES THIS LINE                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### What We Don't Do

| Activity | Industry Standard | Lanite |
|----------|-------------------|--------|
| Voice data upload | Common | **Never** |
| Usage analytics | Common | **Never** |
| Crash reports | Common | **Never** |
| Model telemetry | Some AI tools | **Never** |
| Background recording | Some assistants | **Never** |
| Cloud processing | Most assistants | **Never** |

---

## 3. Data Handling

### Audio Data

| Aspect | Policy |
|--------|--------|
| **Storage** | RAM only during transcription |
| **Persistence** | Never written to disk |
| **Transmission** | Never transmitted over network |
| **Retention** | Zero retention |
| **Access** | Single-process memory isolation |

### Transcription History

Optional history logging is disabled by default. When enabled:

```python
# User must explicitly enable via code modification
# Default behavior: No history logging
```

**History File Security**:
- Stored in user's local directory
- Plain text format (user can encrypt)
- No automatic cloud sync
- User has full control

### Model Data

Whisper models are downloaded once and cached locally:

| Aspect | Policy |
|--------|--------|
| **Source** | HuggingFace (official models) |
| **Storage** | Local cache directory |
| **Network** | Download only, no uploads |
| **Updates** | User-controlled |

### Clipboard Operations

Lanite uses the system clipboard for text injection:

| Risk | Mitigation |
|------|------------|
| Clipboard sniffing | Standard Windows clipboard behavior |
| Data persistence | Clipboard cleared after paste |
| Cross-app access | User-triggered operation only |

---

## 4. Security Features

### Single Instance Lock

Prevents multiple processes from accessing the microphone:

```python
def acquire_single_instance_lock():
    mutex_name = "Lanite_Offline_Voice_Dictation_Mutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    
    if kernel32.GetLastError() == 183:  # Already exists
        print("Lanite is already running. Exiting.")
        sys.exit(0)
```

### Explicit Activation

Recording cannot start without user action:

```python
# Only when BOTH keys are physically held:
if keyboard.is_pressed("ctrl") and keyboard.is_pressed("space"):
    start_recording()
```

### Kill Switch

Immediate termination capability:

```python
# Ctrl + Shift + Space triggers immediate exit
if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift") and keyboard.is_pressed("space"):
    os._exit(0)  # Immediate termination
```

### No Background Services

Lanite runs as a single process with no:
- Background services
- System agents
- Daemon processes
- Scheduled tasks

---

## 5. Known Vulnerabilities

### Current Limitations

| Area | Limitation | Risk Level | Mitigation |
|------|------------|------------|------------|
| **Process Memory** | Audio in RAM during processing | Low | Local-only, brief duration |
| **Clipboard** | Text passes through system clipboard | Low | User-initiated only |
| **Model Security** | Relies on HuggingFace integrity | Low | Official models only |
| **Hotkey Hooking** | Global keyboard hook required | Low | Open-source audit |

### Security Assumptions

Lanite assumes:
1. User's machine is not compromised
2. Windows security features are functional
3. Dependencies are from trusted sources
4. User has physical access control

### Not In Scope

The following are outside Lanite's security model:
- Protecting against compromised operating systems
- Preventing physical access attacks
- Securing against malicious dependencies
- Protecting against targeted sophisticated attacks

---

## 6. Reporting Security Issues

### How to Report

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. Email security concerns to: bhaveshmadisetty@gmail.com
3. Include detailed description and reproduction steps
4. Allow 90 days for response before disclosure

### What to Include

```
Subject: [Security] Brief description

Description:
[Detailed description of the vulnerability]

Steps to Reproduce:
1. Step one
2. Step two
3. ...

Impact:
[What an attacker could accomplish]

Suggested Fix:
[Optional: How you would fix it]

Environment:
- Windows version:
- Python version:
- Lanite version:
```

### Response Timeline

| Stage | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial Assessment | Within 7 days |
| Fix Development | Within 30 days |
| Security Advisory | With next release |

### Recognition

Security researchers who report valid vulnerabilities will be:
- Listed in security acknowledgments (with permission)
- Credited in the relevant release notes
- Eligible for mention in SECURITY.md

---

## 7. Security Updates

### Update Policy

| Issue Severity | Update Timeline |
|----------------|-----------------|
| Critical | Within 24 hours |
| High | Within 7 days |
| Medium | Next scheduled release |
| Low | Next scheduled release |

### Security Advisories

Security advisories are published:
- On GitHub Security tab
- In release notes
- With CVE assignment (if applicable)

### Version Support

| Version | Support Status | Security Updates |
|---------|----------------|------------------|
| 1.0.x | Active | Yes |
| < 1.0 | None | No |

---

## 8. Security Best Practices for Users

### Recommended Configuration

1. **Verify Download Integrity**
   ```bash
   # Check git commit signatures
   git verify-commit HEAD
   ```

2. **Review Dependencies**
   ```bash
   pip install -r requirements.txt --dry-run
   ```

3. **Limit Microphone Access**
   - Use Windows privacy settings
   - Grant microphone access only when needed

4. **Secure History File**
   ```python
   # Disable history logging if not needed
   # Comment out history logging in speech_engine.py
   ```

### Deployment Considerations

For enterprise deployment:

| Consideration | Recommendation |
|---------------|----------------|
| **Model Source** | Host models internally |
| **Dependency Audit** | Use dependency scanning tools |
| **Network Policy** | Block outbound after model download |
| **Process Isolation** | Run in restricted user context |

---

## 9. Third-Party Components

### Dependency Security

| Package | Source | Security Status |
|---------|--------|-----------------|
| faster-whisper | PyPI | Actively maintained |
| sounddevice | PyPI | Stable, minimal attack surface |
| numpy | PyPI | Well-maintained, widely trusted |
| keyboard | PyPI | Open source, auditable |
| pyperclip | PyPI | Minimal code, easy audit |

### Whisper Model Security

Whisper models are:
- Published by OpenAI
- Hosted on HuggingFace
- Downloaded via faster-whisper
- Cached locally after first download

---

## 10. Compliance Considerations

### Privacy Regulations

Lanite's architecture supports compliance with:

| Regulation | Compliance Status |
|------------|-------------------|
| GDPR | **Compliant** - No data leaves device |
| CCPA | **Compliant** - No data collection |
| HIPAA | **Suitable** - Local processing only |
| SOC 2 | **N/A** - No cloud services |

### Enterprise Considerations

For regulated environments:
- No PII transmission
- No third-party data processing
- User-controlled data retention
- Audit trail via optional history logging

---

## Contact

For security-related inquiries:
- Security issues: bhaveshmadisetty@gmail.com
- General questions: GitHub Issues
- Documentation: README.md, ARCHITECTURE.md

---

*Last updated: February 2026*
*Policy version: 1.0*
