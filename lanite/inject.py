# inject.py — Text injection into focused window for Lanite
import ctypes
import logging
import threading
import time
from typing import Optional

import pyperclip
import pyautogui

pyautogui.FAILSAFE = False   # Disable corner-exit so it never fires unexpectedly
pyautogui.PAUSE = 0          # Remove default inter-call pause

# ── Windows API helpers ────────────────────────────────────────────────────────
_u32 = ctypes.windll.user32
_k32 = ctypes.windll.kernel32
try:
    _psapi = ctypes.windll.psapi
except Exception:
    _psapi = None


def get_active_window() -> Optional[int]:
    """Return the HWND of the currently focused window."""
    try:
        return _u32.GetForegroundWindow()
    except Exception:
        return None


def get_active_app_name(hwnd: Optional[int] = None) -> str:
    """Return a friendly process/app name for the given window handle."""
    try:
        if hwnd is None:
            hwnd = _u32.GetForegroundWindow()
        if not hwnd:
            return "Unknown"

        pid = ctypes.c_ulong()
        _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        h_proc = _k32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if h_proc and _psapi:
            buf = ctypes.create_unicode_buffer(260)
            _psapi.GetModuleBaseNameW(h_proc, None, buf, 260)
            _k32.CloseHandle(h_proc)
            name = buf.value.replace(".exe", "").replace(".EXE", "")
            return name.replace("_", " ").title() if name else "Unknown"
    except Exception as e:
        logging.debug(f"get_active_app_name error: {e}")
    return "Unknown"


def _focus_window(hwnd: int):
    """Attempt to bring focus back to a specific window handle."""
    try:
        _u32.SetForegroundWindow(hwnd)
        time.sleep(0.05)
    except Exception:
        pass


def _safe_clipboard_read() -> str:
    """Safely read clipboard content, handling non-text content."""
    for attempt in range(3):
        try:
            content = pyperclip.paste()
            if isinstance(content, str):
                return content
            return ""  # Non-text content
        except Exception as e:
            if attempt == 2:
                logging.debug(f"Clipboard read failed after 3 attempts: {e}")
            time.sleep(0.05)
    return ""


def _safe_clipboard_write(text: str, max_retries: int = 3) -> bool:
    """Safely write to clipboard with retries."""
    for attempt in range(max_retries):
        try:
            pyperclip.copy(text)
            time.sleep(0.05)  # Let clipboard settle
            # Verify the write succeeded
            if pyperclip.paste() == text:
                return True
        except Exception as e:
            logging.debug(f"Clipboard write attempt {attempt + 1} failed: {e}")
            time.sleep(0.05)
    return False


def inject_text(text: str, target_hwnd: Optional[int] = None):
    """
    Inject *text* into the focused (or target) window via clipboard paste.

    Saves and restores the previous clipboard content.
    Uses retry logic for reliability.
    """
    if not text:
        return

    # Save original clipboard
    original = _safe_clipboard_read()
    logging.debug(f"Saved clipboard content: {len(original)} chars")

    try:
        # Copy new text to clipboard with retry
        if not _safe_clipboard_write(text):
            logging.error("Failed to write text to clipboard after retries")
            return

        # Re-focus target window before pasting
        if target_hwnd:
            _focus_window(target_hwnd)

        # Small delay to ensure focus has settled
        time.sleep(0.05)

        # Send Ctrl+V to paste
        pyautogui.hotkey("ctrl", "v")

        # Wait for paste to complete
        time.sleep(0.1)

        logging.info(f"Injected: '{text[:60].strip()}' ({len(text.split())} words)")

    except Exception as e:
        logging.error(f"Text injection failed: {e}")

    finally:
        # Restore clipboard in a separate thread to avoid blocking
        try:
            def _restore():
                time.sleep(0.2)  # Wait for paste to complete
                _safe_clipboard_write(original)
            threading.Thread(target=_restore, daemon=True).start()
        except Exception:
            pass

