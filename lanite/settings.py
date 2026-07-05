# settings.py — Configuration management for Lanite
import json
import os
import sys
import winreg
import logging
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

APP_DATA = Path(os.environ.get('APPDATA', Path.home())) / 'Lanite'
APP_DATA.mkdir(parents=True, exist_ok=True)

MODELS_DIR = APP_DIR / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = APP_DIR / 'assets'
CONFIG_FILE = APP_DATA / 'config.json'

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "model": "small.en",
    "language": "en",
    "remove_fillers": False,
    "startup_with_windows": False,
    "trailing_space": True,
    "first_run": True,
    "compute_type": "int8",
    "preferred_device": None,
}

_config: dict = {}


def load():
    """Load config from %APPDATA%\\Lanite\\config.json, merging defaults."""
    global _config
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                _config = json.load(f)
            for key, val in DEFAULT_CONFIG.items():
                if key not in _config:
                    _config[key] = val
        except Exception as e:
            logging.warning(f"Config load failed ({e}), using defaults")
            _config = DEFAULT_CONFIG.copy()
    else:
        _config = DEFAULT_CONFIG.copy()
        save()


def save():
    """Persist config to disk."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(_config, f, indent=2)
    except Exception as e:
        logging.error(f"Config save failed: {e}")


def get(key: str, default=None):
    return _config.get(key, default)


def set(key: str, value):
    _config[key] = value
    save()


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE_NAME = "Lanite"


def _autostart_command() -> str:
    """
    Build the command string Windows should run at login.

    Uses sys.executable + the resolved main.py location, so both packaged
    (frozen) and source-run installs work no matter which drive/folder they
    live in. Prefers pythonw.exe over python.exe to suppress the console
    window when running from source.
    """
    if getattr(sys, 'frozen', False):
        # Packaged build (e.g. PyInstaller) — just run the built exe itself.
        return f'"{sys.executable}" --minimized'

    py = sys.executable
    # Swap python.exe -> pythonw.exe if it exists alongside, so no console flashes.
    exe_dir = Path(py).parent
    pyw = exe_dir / "pythonw.exe"
    if pyw.exists():
        py = str(pyw)
    return f'"{py}" "{APP_DIR / "main.py"}" --minimized'


def set_startup_with_windows(enabled: bool):
    """Write or remove the Windows autostart registry key."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as reg_key:
            if enabled:
                winreg.SetValueEx(
                    reg_key, _RUN_VALUE_NAME, 0, winreg.REG_SZ, _autostart_command()
                )
            else:
                try:
                    winreg.DeleteValue(reg_key, _RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
        set('startup_with_windows', enabled)
    except Exception as e:
        logging.error(f"Registry startup toggle failed: {e}")


def refresh_autostart_if_stale() -> None:
    """
    Self-heal: if autostart is enabled in config but the registry entry is
    missing OR points to a different path (user moved the folder / reinstalled
    Python), silently rewrite it. Called once at startup from main.py.
    """
    if not get('startup_with_windows', False):
        return
    expected = _autostart_command()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_READ,
        ) as reg_key:
            try:
                current, _ = winreg.QueryValueEx(reg_key, _RUN_VALUE_NAME)
                if current == expected:
                    return  # Already correct — nothing to do
                logging.info(
                    "Autostart entry is stale, rewriting "
                    f"(was: {current[:60]}…)"
                )
            except FileNotFoundError:
                logging.info("Autostart enabled but registry entry missing — recreating")
        # Fall through to write
        set_startup_with_windows(True)
    except Exception as e:
        logging.warning(f"Autostart self-heal check failed: {e}")
