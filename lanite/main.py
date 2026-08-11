# main.py — Entry point and orchestrator for Lanite
"""
Startup sequence:
  1. Load settings + history
  2. Hide tkinter root from taskbar
  3. Create Overlay + Dashboard
  4. Start pynput hotkey listener (Ctrl+Win)
  5. Start pystray tray in daemon thread
  6. Load silero-VAD + Whisper in background thread
  7. If first_run → auto-show Dashboard after 1200ms
  8. tkinter mainloop()

Hotkey flow (Ctrl+Win held/released):
  press  → start audio + show overlay "Listening…"
  release→ stop audio  → VAD → Whisper → inject → hide overlay
           (all post-processing runs in a daemon thread)

Threading rules:
  • tkinter calls ONLY from main thread → use root.after() / action_queue
  • audio, VAD, transcription in daemon threads
  • pystray runs in its own daemon thread
  • pynput runs its own daemon thread
"""

import ctypes
import logging
import os
import queue
import socket
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

# ── Bootstrapping ─────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = str(Path(sys.executable).parent)
else:
    APP_DIR = str(Path(__file__).parent)

os.chdir(APP_DIR)   # make relative imports / paths predictable

# ── Logging (before any other import) ─────────────────────────────────────────
_log_dir = Path(os.environ.get("APPDATA", Path.home())) / "Lanite"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_log_dir / "app.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Suppress noisy debug spam from third-party libs
for _noisy in ("httpcore", "httpx", "PIL", "urllib3", "filelock"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# ── IPC Configuration ─────────────────────────────────────────────────────────
IPC_HOST = '127.0.0.1'
IPC_PORT = 54321

def _send_ipc_message(msg):
    """Send a message to the already-running instance."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((IPC_HOST, IPC_PORT))
            s.sendall(msg.encode('utf-8'))
        return True
    except Exception as e:
        logging.warning(f"IPC send failed: {e}")
        return False


# ── Singleton Check ───────────────────────────────────────────────────────────
# Two independent guards, because a duplicate instance is not a cosmetic
# problem: every instance runs its own hotkey listener and clipboard paste, so
# N instances inject the dictated text N times.
#
#   1. A named mutex — the primary check.
#   2. An exclusive bind on the IPC port — the backstop, in case the mutex is
#      bypassed or its handle was lost (e.g. a hard kill mid-startup).
_keep_alive_mutex = None
_ipc_guard_sock = None


def _port_owned_by_live_instance() -> bool:
    """
    True if another *live* Lanite already owns the IPC port.

    Deliberately does NOT set SO_REUSEADDR: with it, two processes can bind
    the same port on Windows and the guard silently passes. Without it, a
    second bind fails while the first instance is alive, which is exactly the
    signal we want. The socket is kept open for the process lifetime.
    """
    global _ipc_guard_sock
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind((IPC_HOST, IPC_PORT))
        s.listen(5)
        _ipc_guard_sock = s          # Hold it — this IS the IPC listener
        return False
    except OSError as e:
        logging.info(f"IPC port {IPC_PORT} already owned (errno={e.errno})")
        return True


def _check_singleton():
    global _keep_alive_mutex

    bypass = "--no-singleton" in sys.argv
    if bypass:
        # Developer escape hatch. Still warn loudly — running two instances
        # causes double-pasted text, which looks like a transcription bug.
        logging.warning(
            "Singleton check bypassed (--no-singleton) — if another instance "
            "is running, dictated text WILL be pasted twice."
        )
        return

    mutex_name = "Local\\Lanite_New_UI_Mutex"
    _keep_alive_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    err = ctypes.windll.kernel32.GetLastError()
    mutex_taken = (err == 183)  # ERROR_ALREADY_EXISTS

    # Backstop: even if the mutex looked free, refuse to start when another
    # process still owns the IPC port.
    port_taken = _port_owned_by_live_instance()

    if mutex_taken or port_taken:
        logging.info(
            "Another instance is running (mutex=%s, port=%s) — "
            "waking it instead of starting a duplicate."
            % (mutex_taken, port_taken)
        )
        if not _send_ipc_message("show_dashboard"):
            logging.warning("IPC failed; another instance may be stuck.")
        sys.exit(0)

_check_singleton()
logging.info("═══ Lanite v2.0 starting ═══════════════════════════════════")

# ── Module imports ─────────────────────────────────────────────────────────────
# NOTE: `audio` and `transcribe` are deliberately NOT imported here.
# They drag in torch (~2s warm / ~13s cold) and faster_whisper (~3s warm /
# ~70s cold) at module scope, which blocks the tray icon and overlay from
# appearing at all. They are imported inside _load_models(), which runs on a
# background thread, so the UI is live in ~2s instead of ~96s.
import settings as cfg
import history
from inject import get_active_window, get_active_app_name, inject_text
from overlay import Overlay
from tray import SystemTray
from dashboard import Dashboard

if TYPE_CHECKING:  # type-only; never imported at runtime
    from audio import AudioRecorder, VADProcessor
    from transcribe import Transcriber

# ── App-wide state ─────────────────────────────────────────────────────────────
_action_q: queue.Queue = queue.Queue()

_recording = False
_busy      = False          # True while VAD/transcription is running
_target_hwnd: int | None = None
_target_app:  str        = "Unknown"
_device_scan_done = False   # First-run mic scan is deferred until first hotkey

# Loaded in background thread; access safely
_recorder:    "AudioRecorder | None" = None
_vad:         "VADProcessor  | None" = None
_transcriber: "Transcriber   | None" = None
_tray:        SystemTray     | None  = None
_overlay:     Overlay        | None  = None
_dashboard:   Dashboard      | None  = None
_root = None

# Set once the Whisper model is loaded and ready to transcribe.
_models_ready = threading.Event()

# True once we've told the user "still loading" for the current key-hold.
# Key-down auto-repeat fires _on_press many times per second while the hotkey
# is held, so without this latch every repeat queued another "start" and
# produced another notification (and another notification sound).
_loading_warned = False


# ── Hotkey state tracking ─────────────────────────────────────────────────────
class _Hotkey:
    ctrl  = False
    win   = False
    armed = False   # True between combo-down and the next modifier release


# ── Hotkey callbacks (pynput thread) ──────────────────────────────────────────
def _on_press(key):
    """
    Called in pynput's daemon thread for every key-down event.

    Windows fires key-down repeatedly while a key is held, so this runs many
    times per second during a single hotkey hold. _Hotkey.armed makes the
    combo edge-triggered: we queue exactly one "start" per press, and don't
    re-arm until a modifier is actually released.
    """
    global _recording, _busy
    try:
        from pynput.keyboard import Key

        # Track both left and right modifier keys
        if key in (Key.ctrl_l, Key.ctrl_r):
            _Hotkey.ctrl = True
        elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            _Hotkey.win = True
        else:
            return  # Not part of the combo — ignore entirely

        if (_Hotkey.ctrl and _Hotkey.win
                and not _Hotkey.armed
                and not _recording and not _busy):
            _Hotkey.armed = True          # Latch: ignore auto-repeat
            logging.info("Hotkey combo detected → queuing START")
            _action_q.put(("start",))

    except Exception:
        pass


def _on_release(key):
    """Called in pynput's daemon thread for every key-up event."""
    global _loading_warned
    try:
        from pynput.keyboard import Key

        is_ctrl = key in (Key.ctrl_l, Key.ctrl_r)
        is_win  = key in (Key.cmd, Key.cmd_l, Key.cmd_r)
        if not (is_ctrl or is_win):
            return

        if is_ctrl:
            _Hotkey.ctrl = False
            logging.debug("Hotkey: Ctrl released")
        else:
            _Hotkey.win = False
            logging.debug(f"Hotkey: Win released (recording={_recording})")
            if _recording:
                logging.info("Hotkey combo released → queuing STOP")
                _action_q.put(("stop",))

        # Either modifier going up ends this hold: re-arm for the next press
        # and allow one fresh "still loading" notice next time.
        _Hotkey.armed = False
        _loading_warned = False

    except Exception as e:
        logging.debug(f"_on_release error: {e}")


# ── Background: One-shot device scan on first hotkey ─────────────────────────
def _deferred_device_scan():
    """
    Run find_best_device() the first time the user presses Ctrl+Win,
    then queue an immediate "start" so the very first press still records.
    Runs in a daemon thread so the hotkey callback returns instantly.
    """
    global _device_scan_done
    try:
        from audio import find_best_device

        if _tray:
            _tray.notify("Lanite v2.0", "Detecting your microphone…")
        logging.info("Deferred mic scan starting (first hotkey press)")
        best = find_best_device()
        if best is not None and _recorder:
            _recorder.set_device(best)
            cfg.set("preferred_device", best)
            logging.info(f"Auto-selected device index {best}")
        else:
            logging.warning("Scan found no active mic — using system default")
    except Exception as e:
        logging.error(f"Deferred device scan failed: {e}")
    finally:
        _device_scan_done = True
        # Only kick off recording if the user is still holding the hotkey.
        # If they released while we were scanning, don't record a phantom clip.
        if _Hotkey.ctrl and _Hotkey.win:
            _action_q.put(("start",))
        else:
            if _tray:
                _tray.notify("Lanite v2.0", "Mic ready — press Ctrl+Win to speak")


# ── Background: stop stream, then VAD + Transcription ─────────────────────────
def _stop_and_transcribe():
    """
    Runs in a daemon thread. Closes the mic stream (which can block on the
    audio backend) and resamples off the main thread, so the overlay keeps
    animating instead of freezing, then hands off to the usual pipeline.
    """
    global _busy
    try:
        audio_data = (
            _recorder.stop() if (_recorder and _recorder.is_valid) else None
        )
    except Exception as e:
        logging.error(f"Recorder stop failed: {e}")
        _busy = False
        _action_q.put(("hide_overlay",))
        return

    _transcribe_and_inject(audio_data)


# ── Background: VAD + Transcription ───────────────────────────────────────────
def _transcribe_and_inject(audio_data):
    """Runs in a daemon thread. Puts results into action queue for main thread."""
    global _busy
    try:
        if audio_data is None or len(audio_data) == 0:
            logging.info("Empty audio buffer — discarding")
            return

        # VAD
        speech = _vad.process(audio_data) if _vad else audio_data
        if speech is None:
            logging.info("No speech detected — discarding")
            return

        # Transcription
        text, elapsed = _transcriber.transcribe(
            speech,
            language=cfg.get("language", "en"),
            remove_fillers=cfg.get("remove_fillers", False),
            trailing_space=cfg.get("trailing_space", True),
        ) if _transcriber else ("", 0.0)

        if text and text.strip():
            inject_text(text, target_hwnd=_target_hwnd)
            history.add_entry(text.strip(), _target_app, elapsed)
            _action_q.put(("refresh_dashboard",))
        else:
            logging.info("Empty transcription — nothing to inject")

    except Exception as e:
        logging.error(f"Transcription/inject error: {e}")
    finally:
        _busy = False
        _action_q.put(("hide_overlay",))


# ── IPC Listener ───────────────────────────────────────────────────────────────
def _ipc_listener():
    """
    Listen for wake-up signals from secondary instances. Runs in daemon thread.

    Reuses the socket _check_singleton() already bound exclusively. Rebinding
    here would need SO_REUSEADDR, which is what let two instances share the
    port and defeated the singleton backstop.
    """
    server = _ipc_guard_sock
    if server is None:
        # Only happens under --no-singleton, where the guard was skipped.
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            server.bind((IPC_HOST, IPC_PORT))
            server.listen(5)
        except OSError as e:
            logging.warning(f"IPC listener disabled (port unavailable): {e}")
            return

    server.settimeout(None)
    logging.info(f"IPC listener active on port {IPC_PORT}")

    consecutive_errors = 0
    try:
        while True:
            try:
                conn, _addr = server.accept()
                consecutive_errors = 0
                with conn:
                    conn.settimeout(2.0)
                    data = conn.recv(1024)
                    if data:
                        msg = data.decode('utf-8').strip()
                        logging.info(f"IPC received: '{msg}'")
                        if msg == "show_dashboard":
                            _action_q.put(("show_dashboard",))
            except Exception as e:
                # Back off instead of spinning: a persistently failing accept()
                # used to busy-loop this thread at 100% CPU.
                consecutive_errors += 1
                logging.debug(f"IPC accept error: {e}")
                if consecutive_errors >= 5:
                    logging.error("IPC listener failing repeatedly — stopping")
                    return
                import time
                time.sleep(min(1.0, 0.1 * consecutive_errors))
    except Exception as e:
        logging.error(f"IPC listener crashed: {e}")
    finally:
        try:
            server.close()
        except Exception:
            pass


# ── Background: Model loading (device scan deferred to first hotkey) ────────
def _load_models():
    global _vad, _transcriber

    # Heavy imports happen here, on this background thread, so the tray icon
    # and overlay are already on screen while torch/faster_whisper load.
    from audio import VADProcessor
    from transcribe import Transcriber

    # ── Step 1: Apply saved device preference (no scan, no stream open) ──
    preferred_device = cfg.get("preferred_device", None)
    if preferred_device is not None:
        logging.info(f"Using saved device index: {preferred_device}")
        if _recorder:
            _recorder.set_device(preferred_device)
    else:
        logging.info("No saved mic preference — will scan on first Ctrl+Win press")

    # ── Step 2: Load VAD ─────────────────────────────────────────────────
    logging.info("Loading silero-VAD…")
    _vad = VADProcessor(app_dir=APP_DIR)
    _vad.load()

    # ── Step 3: Load Whisper ───────────────────────────────────────────────
    logging.info("Loading Whisper model…")
    _transcriber = Transcriber(
        models_dir=str(cfg.MODELS_DIR),
        compute_type=cfg.get("compute_type", "int8"),
        beam_size=cfg.get("beam_size", 1),
    )
    ok = _transcriber.load(cfg.get("model", "small.en"))

    if ok:
        _models_ready.set()
        logging.info("All models loaded — Lanite v2.0 ready")
        if _tray:
            _tray.notify("Lanite v2.0", "Ready — Ctrl+Win to speak")
        _action_q.put(("status", "Ready — Ctrl+Win to speak", None))
        if not (_recorder and _recorder.is_valid):
            if _tray:
                _tray.notify("Lanite v2.0", "⚠ No microphone detected")
    else:
        logging.error("Whisper model failed to load")
        if _tray:
            _tray.notify("Lanite v2.0", "⚠ Model failed — see app.log")
        _action_q.put(("status", "⚠ Model failed — see app.log", "#ef4444"))


# ── Main-thread action queue processor ────────────────────────────────────────
def _process_queue():
    global _recording, _busy, _target_hwnd, _target_app, _loading_warned

    try:
        while True:
            item = _action_q.get_nowait()
            action = item[0]

            if action == "start" and not _recording and not _busy:
                # Don't start capturing until Whisper can actually transcribe.
                # Previously the hotkey listener went live while _load_models()
                # was still running, so an early press recorded real speech,
                # ran VAD on it, then hit "Transcriber not loaded" and dropped
                # it silently. Tell the user we're not ready instead.
                if not _models_ready.is_set():
                    # Silent overlay only — no tray notification. Toasts play a
                    # system sound, and this can legitimately fire on each
                    # distinct press while the model loads.
                    if not _loading_warned:
                        _loading_warned = True
                        logging.info("Hotkey pressed before models ready — ignoring")
                        if _overlay:
                            _overlay.show_loading()
                    continue

                # First-ever hotkey press with no saved device: run the scan
                # once on a background thread, then it re-queues "start".
                if (not _device_scan_done
                        and cfg.get("preferred_device", None) is None):
                    threading.Thread(
                        target=_deferred_device_scan,
                        daemon=True,
                        name="device-scan",
                    ).start()
                    continue  # Don't record yet — scan thread will re-queue
                _recording = True
                # Capture focused window BEFORE overlay appears
                _target_hwnd = get_active_window()
                _target_app  = get_active_app_name(_target_hwnd)
                logging.info(f"Recording → {_target_app}")
                if _recorder and _recorder.is_valid:
                    _recorder.start()
                if _overlay:
                    _overlay.show_listening()

            elif action == "stop" and _recording:
                _recording = False
                _busy = True
                if _overlay:
                    _overlay.show_processing()
                # NOTE: _recorder.stop() closes the audio stream and resamples
                # the whole buffer (44.1k -> 16k). Both can block for seconds,
                # and doing that here froze the tkinter main thread — the
                # overlay stopped animating and the app looked hung. It now
                # runs inside the worker thread.
                threading.Thread(
                    target=_stop_and_transcribe,
                    daemon=True,
                    name="transcribe",
                ).start()

            elif action == "hide_overlay":
                _busy = False
                if _overlay:
                    _overlay.hide()

            elif action == "refresh_dashboard":
                if _dashboard:
                    _dashboard.refresh()

            elif action == "show_dashboard":
                if _dashboard:
                    _dashboard.show()

            elif action == "status":
                _, text, color = item
                if _dashboard:
                    _dashboard.update_status(text, color)

            elif action == "toggle_dictation":
                if _recording:
                    # Stop — same off-thread teardown as the hotkey path.
                    _recording = False
                    _busy = True
                    if _overlay:
                        _overlay.show_processing()
                    threading.Thread(
                        target=_stop_and_transcribe,
                        daemon=True,
                        name="transcribe",
                    ).start()
                else:
                    # Start — same readiness gate as the hotkey path.
                    if not _models_ready.is_set():
                        logging.info("Toggle-dictation before models ready — ignoring")
                        if _overlay:
                            _overlay.show_loading()
                        continue
                    _recording = True
                    _target_hwnd = get_active_window()
                    _target_app = get_active_app_name(_target_hwnd)
                    logging.info(f"Recording -> {_target_app}")
                    if _recorder and _recorder.is_valid:
                        _recorder.start()
                    if _overlay:
                        _overlay.show_listening()

            elif action == "clear_history":
                history.clear()
                logging.info("History cleared")

    except queue.Empty:
        pass

    _root.after(40, _process_queue)


# ── Force Stop ────────────────────────────────────────────────────────────────
def _force_stop():
    logging.info("Force stop triggered")
    if _tray:
        _tray.stop()
    try:
        _root.quit()
    except Exception:
        pass
    os._exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    global _recorder, _overlay, _dashboard, _tray, _root

    # ── Config + history ──────────────────────────────────────────────────────
    cfg.load()
    history.load()
    logging.info(f"Config: model={cfg.get('model')}, lang={cfg.get('language')}")

    # ── Self-heal autostart entry (fixes stale registry if the folder moved) ──
    cfg.refresh_autostart_if_stale()

    # ── Hidden tkinter root ───────────────────────────────────────────────────
    import tkinter as tk
    _root = tk.Tk()
    _root.withdraw()
    _root.wm_attributes("-alpha", 0)

    # Permanently remove root from taskbar
    _root.update_idletasks()
    try:
        hwnd = _root.winfo_id()
        GWL_EXSTYLE      = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW  = 0x00040000
        cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            (cur | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW,
        )
    except Exception as e:
        logging.warning(f"Root taskbar removal: {e}")

    # ── AudioRecorder (checks mic availability) ───────────────────────────────
    # Local import: audio.py only needs sounddevice/numpy at module scope
    # (~0.4s). torch is imported lazily inside VADProcessor.load().
    from audio import AudioRecorder

    _recorder = AudioRecorder()
    if not _recorder.is_valid:
        logging.warning("No microphone detected at startup")

    # ── Overlay ───────────────────────────────────────────────────────────────
    _overlay = Overlay(_root, amplitude_getter=_recorder.get_amplitude)

    # ── Shared model-swap trigger (used by both dashboard and tray) ──────────
    def _swap_model(name: str):
        def _worker():
            if not _transcriber:
                return
            # Publish progress so the dashboard can show a real loading state
            # rather than claiming success the moment the card is clicked.
            if _dashboard:
                _dashboard.set_model_state("loading", name)
            _action_q.put(("status", f"Loading {name}…", "#f5c451"))

            # reload() drops the old model first, so block recording for the
            # duration — otherwise the pre-load race reopens mid-swap.
            _models_ready.clear()
            t0 = time.perf_counter()
            ok = _transcriber.reload(name)
            took = time.perf_counter() - t0
            if ok:
                _models_ready.set()

            if _dashboard:
                _dashboard.set_model_state("ready" if ok else "error", name)
            _action_q.put((
                "status",
                f"Ready · {name}" if ok else f"⚠ Failed to load {name}",
                None if ok else "#ef4444",
            ))
            if _tray:
                _tray.notify(
                    "Lanite v2.0",
                    f"Now using {name} ({took:.1f}s)" if ok
                    else f"⚠ Failed to load {name}",
                )
            logging.info(f"Model swap -> {name}: ok={ok} in {took:.2f}s")
        threading.Thread(target=_worker, daemon=True, name="model-reload").start()

    # ── Dashboard ─────────────────────────────────────────────────────────────
    _dashboard = Dashboard(
        _root,
        on_force_stop=_force_stop,
        on_model_change=_swap_model,
    )

    # ── System Tray (daemon thread) ───────────────────────────────────────────
    icon_path = os.path.join(APP_DIR, "assets", "lanite_icon.png")
    _tray = SystemTray(
        icon_path=icon_path,
        settings=cfg,
        on_dashboard=lambda: _action_q.put(("show_dashboard",)),
        on_quit=_force_stop,
        on_toggle_dictation=lambda: _action_q.put(("toggle_dictation",)),
        on_clear_history=lambda: _action_q.put(("clear_history",)),
        on_model_change=_swap_model,
    )
    threading.Thread(target=_tray.run, daemon=True, name="tray").start()

    # ── Startup notification ──────────────────────────────────────────────────
    _root.after(1500, lambda: _tray.notify("Lanite v2.0", "Voice Typing is running in the background"))

    # ── Model loading (daemon thread) ─────────────────────────────────────────
    threading.Thread(target=_load_models, daemon=True, name="model-loader").start()

    # ── Pynput hotkey listener ────────────────────────────────────────────────
    from pynput.keyboard import Listener
    listener = Listener(on_press=_on_press, on_release=_on_release)
    listener.daemon = True
    listener.start()
    logging.info("Hotkey listener started (Ctrl+Win)")

    # ── Start IPC Listener ────────────────────────────────────────────────────
    threading.Thread(target=_ipc_listener, daemon=True, name="ipc-listener").start()

    # ── Initial UI display logic ──────────────────────────────────────────────
    if "--minimized" not in sys.argv:
        # User manually launched — show dashboard after tkinter has settled
        _root.after(1200, _safe_show_dashboard)

    # ── Start action-queue polling ────────────────────────────────────────────
    _root.after(100, _process_queue)

    # ── Run ───────────────────────────────────────────────────────────────────
    logging.info("Entering tkinter mainloop")
    try:
        _root.mainloop()
    except KeyboardInterrupt:
        pass

    logging.info("Lanite v2.0 exiting")
    os._exit(0)


def _safe_show_dashboard():
    """Show the dashboard safely."""
    global _dashboard
    if _dashboard is None:
        return
    try:
        _dashboard.show()
    except Exception as e:
        logging.warning(f"_safe_show_dashboard error: {e}")


if __name__ == "__main__":
    main()
