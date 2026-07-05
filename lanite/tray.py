# tray.py — System tray icon and menu for Lanite
import logging
import os
from typing import Callable

import pystray
from PIL import Image, ImageFilter
from typing import Optional


class SystemTray:
    """
    Manages the pystray tray icon.

    Menu layout (user-centric, most-used items at top):
      Lanite — Voice Typing  (disabled label, shows status)
      ──────────────────────
      Start / Stop Dictation  (toggle, primary action)
      Force Stop              (emergency stop, top-level)
      ──────────────────────
      Model  ▶  tiny.en / small.en ✓ / medium.en
      Language  ▶  English ✓ / Auto-detect
      Remove Fillers  [toggle]
      Start with Windows  [toggle]
      ──────────────────────
      Dashboard
      Clear History
      ──────────────────────
      Quit
    """

    def __init__(
        self,
        icon_path: str,
        settings,                       # settings module
        on_dashboard: Callable,
        on_quit: Callable,
        on_toggle_dictation: Callable,
        on_clear_history: Callable,
        on_model_change: Optional[Callable] = None,
    ):
        self._settings = settings
        self._on_dashboard = on_dashboard
        self._on_quit = on_quit
        self._on_toggle_dictation = on_toggle_dictation
        self._on_clear_history = on_clear_history
        self._on_model_change = on_model_change
        self._tray: Optional[pystray.Icon] = None
        self._icon_img = self._load_icon(icon_path)
        self._is_recording = False
        self._status_text = "Ready"

    # ── Icon ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _load_icon(path: str) -> Image.Image:
        try:
            img = Image.open(path).convert("RGBA")
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            logging.error(f"Tray icon load failed: {e}")
            # Minimal blue square fallback
            img = Image.new("RGBA", (64, 64), (26, 115, 232, 255))
            return img

    # ── Menu builder ──────────────────────────────────────────────────────────
    def _build_menu(self) -> pystray.Menu:
        s = self._settings
        logging.info(f"Building tray menu - recording={self._is_recording}, status={self._status_text}")

        def set_model(name):
            def _inner(icon, item):
                if s.get("model") == name:
                    return
                s.set("model", name)
                icon.update_menu()
                if self._on_model_change:
                    logging.info(f"Tray: switching Whisper model -> {name}")
                    self._on_model_change(name)
            return _inner

        def set_language(lang):
            def _inner(icon, item):
                s.set("language", lang)
                icon.update_menu()
            return _inner

        def toggle_fillers(icon, item):
            s.set("remove_fillers", not s.get("remove_fillers"))
            icon.update_menu()

        def toggle_startup(icon, item):
            s.set_startup_with_windows(not s.get("startup_with_windows"))
            icon.update_menu()

        def open_dashboard(icon, item):
            self._on_dashboard()

        def toggle_dictation(icon, item):
            self._is_recording = not self._is_recording
            self._status_text = "Recording..." if self._is_recording else "Ready"
            self._on_toggle_dictation()
            icon.update_menu()

        def force_stop(icon, item):
            self._is_recording = False
            self._status_text = "Ready"
            self._on_quit()
            icon.update_menu()

        def clear_history(icon, item):
            self._on_clear_history()

        return pystray.Menu(
            pystray.MenuItem(f"Lanite v2.0 — {self._status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Stop Recording" if self._is_recording else "Start Dictation",
                toggle_dictation,
            ),
            pystray.MenuItem("Force Stop", force_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Model", pystray.Menu(
                pystray.MenuItem(
                    "tiny.en  (~150 MB)",
                    set_model("tiny.en"),
                    checked=lambda item: s.get("model") == "tiny.en",
                    radio=True,
                ),
                pystray.MenuItem(
                    "small.en  (~500 MB)",
                    set_model("small.en"),
                    checked=lambda item: s.get("model") == "small.en",
                    radio=True,
                ),
                pystray.MenuItem(
                    "medium.en  (~1.5 GB)",
                    set_model("medium.en"),
                    checked=lambda item: s.get("model") == "medium.en",
                    radio=True,
                ),
            )),
            pystray.MenuItem("Language", pystray.Menu(
                pystray.MenuItem(
                    "English",
                    set_language("en"),
                    checked=lambda item: s.get("language") == "en",
                    radio=True,
                ),
                pystray.MenuItem(
                    "Auto-detect",
                    set_language("auto"),
                    checked=lambda item: s.get("language") == "auto",
                    radio=True,
                ),
            )),
            pystray.MenuItem(
                "Remove Fillers",
                toggle_fillers,
                checked=lambda item: bool(s.get("remove_fillers")),
            ),
            pystray.MenuItem(
                "Start with Windows",
                toggle_startup,
                checked=lambda item: bool(s.get("startup_with_windows")),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Dashboard", open_dashboard),
            pystray.MenuItem("Clear History", clear_history),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: self.stop()),
        )

    # ── Public API ────────────────────────────────────────────────────────────
    def notify(self, title: str, message: str):
        """Show a tray balloon / native notification."""
        if self._tray:
            try:
                self._tray.notify(message, title)
            except Exception as e:
                logging.debug(f"Tray notify failed: {e}")

    def run(self):
        """Start the tray icon (blocking — run in a daemon thread)."""
        self._tray = pystray.Icon(
            name="lanite",
            icon=self._icon_img,
            title="Lanite v2.0 — Voice Typing",
            menu=self._build_menu(),
        )
        self._tray.run()

    def stop(self):
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass

    # ── Status updates ──────────────────────────────────────────────────────
    def set_recording(self, active: bool):
        """Update recording state and refresh tray icon/menu."""
        self._is_recording = active
        self._status_text = "Recording..." if active else "Ready"
        if self._tray:
            try:
                self._tray.title = f"Lanite v2.0 — {'🔴 Recording' if active else 'Voice Typing'}"
                self._tray.icon = self._make_icon(active)
                self._tray.update_menu()
            except Exception:
                pass

    @staticmethod
    def _make_icon(recording: bool) -> Image.Image:
        """Generate a tray icon: blue when idle, red when recording."""
        color = (220, 50, 50, 255) if recording else (26, 115, 232, 255)
        img = Image.new("RGBA", (64, 64), color)
        # Draw a white circle in the center to resemble a mic/record button
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        d.ellipse([16, 16, 48, 48], fill=(255, 255, 255, 180))
        return img
