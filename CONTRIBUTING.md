# Contributing to Lanite

Thank you for your interest in contributing to Lanite! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How to Contribute](#how-to-contribute)
3. [Development Environment](#development-environment)
4. [Code Style Guidelines](#code-style-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Bug Reports](#bug-reports)
7. [Feature Requests](#feature-requests)
8. [Development Roadmap](#development-roadmap)

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

### Summary

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

---

## How to Contribute

### Types of Contributions

| Type | Description |
|------|-------------|
| **Bug Fixes** | Fix issues in existing code |
| **Features** | Add new functionality |
| **Documentation** | Improve or translate documentation |
| **Testing** | Add tests or improve test coverage |
| **Performance** | Optimize code for speed/memory |
| **Accessibility** | Improve usability for all users |

### Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch
5. Make your changes
6. Submit a pull request

---

## Development Environment

### Prerequisites

- Python 3.8+ (3.10 recommended)
- Git
- Windows 10/11
- Virtual environment tooling

### Setup Steps

```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/lanite.git
cd lanite

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Verify installation
python main.py
```

### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `black` | Code formatting |
| `flake8` | Linting |
| `mypy` | Type checking |

---

## Code Style Guidelines

### Python Style

Lanite follows PEP 8 with some modifications:

**Formatting**:
- Maximum line length: 88 characters (Black default)
- Use 4 spaces for indentation (no tabs)
- Use double quotes for strings

**Naming Conventions**:
```python
# Functions: snake_case
def transcribe_audio(audio_data):
    pass

# Classes: PascalCase
class AudioProcessor:
    pass

# Constants: UPPER_SNAKE_CASE
SAMPLE_RATE = 16000

# Private functions: _leading_underscore
def _internal_helper():
    pass
```

**Docstrings**:
```python
def process_audio(audio_data, sample_rate=16000):
    """
    Process audio data for transcription.
    
    Args:
        audio_data: Numpy array containing audio samples
        sample_rate: Audio sample rate in Hz (default: 16000)
    
    Returns:
        Transcribed text string
    
    Raises:
        ValueError: If audio_data is empty
    
    Example:
        >>> text = process_audio(audio_array)
        >>> print(text)
        'Hello world'
    """
    pass
```

**Imports**:
```python
# Standard library first
import os
import sys
import threading

# Third-party packages second
import numpy as np
from faster_whisper import WhisperModel

# Local modules last
import config
from text_processor import process
```

### Code Quality Checks

Before submitting, run:

```bash
# Format code
black *.py

# Check for issues
flake8 *.py --max-line-length=88

# Type checking (optional)
mypy *.py --ignore-missing-imports
```

---

## Pull Request Process

### Branch Naming

Use descriptive branch names:

```
feature/add-language-support
fix/clipboard-race-condition
docs/improve-installation-guide
test/add-unit-tests
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples**:
```
feat(engine): add support for GPU inference

- Add CUDA device detection
- Implement GPU memory management
- Update config with device option

Closes #42
```

### Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are descriptive
- [ ] PR description explains changes
- [ ] Related issues are linked

### Review Process

1. Submit PR with clear description
2. Maintainers review within 7 days
3. Address any feedback
4. Once approved, PR will be merged

### PR Template

```markdown
## Description
[Describe your changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
[Describe how you tested these changes]

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes

## Related Issues
Closes #[issue number]
```

---

## Bug Reports

### Before Reporting

1. Check existing issues
2. Try latest version
3. Run diagnostics: `python check_mic.py`

### Bug Report Template

```markdown
## Description
[Clear description of the bug]

## Steps to Reproduce
1. Step one
2. Step two
3. Expected behavior

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Windows version: [e.g., Windows 10 21H2]
- Python version: [e.g., 3.10.5]
- Lanite version: [e.g., 1.0.0]
- Model: [e.g., tiny.en]

## Logs
```
[Paste relevant log output]
```

## Additional Context
[Any other relevant information]
```

---

## Feature Requests

### Before Requesting

1. Check existing feature requests
2. Verify it aligns with project goals
3. Consider implementation complexity

### Feature Request Template

```markdown
## Problem Statement
[Describe the problem this feature would solve]

## Proposed Solution
[Describe your proposed solution]

## Alternatives Considered
[Other solutions you've considered]

## Use Case
[Describe how this feature would be used]

## Additional Context
[Any other relevant information]
```

---

## Development Roadmap

### Current Priorities

| Priority | Area | Status |
|----------|------|--------|
| High | Stability improvements | In Progress |
| High | Documentation | Ongoing |
| Medium | Performance optimization | Planned |
| Medium | GPU support | Planned |
| Low | Multi-language support | Future |

### Future Goals

1. **Configuration UI**: Settings window for easy customization
2. **Model Management**: Download and switch models within the app
3. **Language Support**: Support for non-English languages
4. **Streaming Transcription**: Real-time text display during speech
5. **System Tray Integration**: Minimize to tray with status icon

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_text_processor.py
```

### Writing Tests

```python
# tests/test_text_processor.py
import pytest
from text_processor import process, remove_fillers

class TestTextProcessor:
    """Tests for text processing functions."""
    
    def test_remove_fillers_basic(self):
        """Test basic filler removal."""
        result = remove_fillers("um hello world")
        assert result == "hello world"
    
    def test_process_capitalization(self):
        """Test sentence capitalization."""
        result = process("hello world")
        assert result[0] == 'H'
    
    def test_empty_input(self):
        """Test empty string handling."""
        assert process("") == ""
```

---

## Documentation

### Documentation Structure

```
docs/
├── README.md           # Project overview
├── INSTALLATION.md     # Setup instructions
├── USAGE.md            # User guide
├── ARCHITECTURE.md     # Technical design
├── PROJECT_REPORT.md   # Development history
├── CONTRIBUTING.md     # This file
├── CHANGELOG.md        # Version history
├── ROADMAP.md          # Future plans
├── SECURITY.md         # Security policy
└── CODE_OF_CONDUCT.md  # Community guidelines
```

### Writing Guidelines

- Use clear, concise language
- Include code examples where helpful
- Update all relevant docs when changing functionality
- Check spelling and grammar

---

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search closed issues
3. Open a new issue with the "question" label

---

## Recognition

Contributors are recognized in:

- Git commit history
- Release notes for significant contributions
- Project README (for major contributions)

Thank you for helping make Lanite better!
