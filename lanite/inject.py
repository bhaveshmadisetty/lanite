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
    """
    Bring focus back to a specific window handle.

    Polls GetForegroundWindow rather than sleeping blind — focus usually
    settles in a few ms, and we only pay the full wait when it doesn't.
    """
    try:
        if _u32.GetForegroundWindow() == hwnd:
            return  # Already focused — nothing to wait for
        _u32.SetForegroundWindow(hwnd)
        deadline = time.perf_counter() + 0.12
        while time.perf_counter() < deadline:
            if _u32.GetForegroundWindow() == hwnd:
                return
            time.sleep(0.005)
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
    """
    Safely write to clipboard with retries.

    Polls for the write to land instead of sleeping a flat 50ms: the clipboard
    is usually ready within a few ms, so this returns as soon as it verifies
    rather than always paying worst-case latency.
    """
    for attempt in range(max_retries):
        try:
            pyperclip.copy(text)
            deadline = time.perf_counter() + 0.15
            while time.perf_counter() < deadline:
                if pyperclip.paste() == text:
                    return True
                time.sleep(0.005)
        except Exception as e:
            logging.debug(f"Clipboard write attempt {attempt + 1} failed: {e}")
            time.sleep(0.02)
    return False


_VK_CONTROL = 0x11
_VK_LWIN    = 0x5B
_VK_RWIN    = 0x5C


def _key_is_down(vk: int) -> bool:
    """True if the given virtual key is physically held down right now."""
    try:
        return bool(_u32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def _wait_for_modifiers_released(timeout: float = 1.0):
    """
    Block until Ctrl and Win are released (or *timeout* elapses).

    Transcription usually finishes after the user has let go, so this
    normally returns immediately.
    """
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if not (_key_is_down(_VK_CONTROL)
                or _key_is_down(_VK_LWIN)
                or _key_is_down(_VK_RWIN)):
            return
        time.sleep(0.01)
    logging.debug("Modifiers still held after timeout — pasting anyway")


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

        # Re-focus target window before pasting (polls internally)
        if target_hwnd:
            _focus_window(target_hwnd)

        # Wait for the user to actually let go of the activation hotkey.
        # Synthesising Ctrl+V while Ctrl and Win are still physically down can
        # be delivered as Ctrl+Win+V (a Windows shortcut) or swallowed
        # entirely, so the paste lands in the wrong place or not at all.
        _wait_for_modifiers_released()

        # Send Ctrl+V to paste
        pyautogui.hotkey("ctrl", "v")

        # Brief settle so the paste is consumed before we restore the
        # clipboard below. Trimmed from 100ms — the restore is already
        # deferred on its own thread.
        time.sleep(0.03)

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

