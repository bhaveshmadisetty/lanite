# history.py — Dictation history management for Lanite
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import settings as cfg

HISTORY_FILE = cfg.APP_DATA / 'history.json'
MAX_ENTRIES = 100

_history: List[Dict] = []


def load():
    """Load history from disk."""
    global _history
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                _history = json.load(f)
        except Exception as e:
            logging.warning(f"History load failed: {e}")
            _history = []


def _save():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(_history[-MAX_ENTRIES:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"History save failed: {e}")


def add_entry(text: str, app_name: str, duration_seconds: float) -> Dict:
    """Record a completed dictation."""
    text = text.strip()
    word_count = len(text.split()) if text else 0
    entry = {
        "timestamp": datetime.now().isoformat(),
        "app_name": app_name,
        "word_count": word_count,
        "duration_seconds": round(duration_seconds, 2),
        "text": text,
        "preview": (text[:60] + "…") if len(text) > 60 else text,
    }
    _history.append(entry)
    _save()
    return entry


def clear() -> None:
    """Erase all dictation history and persist the empty state."""
    global _history
    _history = []
    _save()


def get_all() -> List[Dict]:
    """Return all entries, most recent first."""
    return list(reversed(_history))


def get_stats() -> Dict:
    today = datetime.now().date().isoformat()
    today_entries = [e for e in _history if e.get('timestamp', '')[:10] == today]
    total_words = sum(e.get('word_count', 0) for e in _history)
    sessions_today = len(today_entries)
    durations = [e.get('duration_seconds', 0) for e in _history if e.get('duration_seconds', 0) > 0]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0
    return {
        "total_words": total_words,
        "sessions_today": sessions_today,
        "avg_duration": avg_duration,
        "total_sessions": len(_history),
    }
