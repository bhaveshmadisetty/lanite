# transcribe.py — faster-whisper wrapper for Lanite
import logging
import os
import re
import threading
import time
from typing import Optional, Tuple

import numpy as np

# Single-word fillers (fast path — checked after multi-word)
_FILLER_SINGLE = frozenset({
    "um", "uh", "hmm", "hm", "like", "so",
    "basically", "literally", "actually", "right", "okay",
})
# Multi-word fillers removed via phrase substitution before word-split
_FILLER_MULTI = ["you know"]


class Transcriber:
    """
    Wraps faster-whisper WhisperModel.

    - Model is loaded *once* at startup and kept in RAM.
    - On CPU with int8: ~2-3s for 10s of speech.
    - Returns (text, elapsed_seconds) tuple.
    """

    def __init__(self, models_dir: str, compute_type: str = "int8"):
        self.models_dir = models_dir
        self.model = None
        self._current_model_name: Optional[str] = None
        self._compute_type = compute_type
        self._lock = threading.Lock()

    # ── Loading ───────────────────────────────────────────────────────
    def load(self, model_name: str = "small.en") -> bool:
        self._current_model_name = model_name
        try:
            from faster_whisper import WhisperModel

            # Check for a pre-downloaded local copy first
            local_path = os.path.join(self.models_dir, model_name)
            if os.path.isdir(local_path) and os.listdir(local_path):
                model_arg = local_path
                logging.info(f"Loading Whisper from local: {local_path}")
            else:
                model_arg = model_name      # faster-whisper will download
                logging.info(f"Downloading Whisper model '{model_name}' -> {self.models_dir}")

            self.model = WhisperModel(
                model_size_or_path=model_arg,
                device="cpu",
                compute_type=self._compute_type,
                download_root=self.models_dir,
                num_workers=1,
            )
            logging.info(f"Whisper '{model_name}' ready")
            return True
        except Exception as e:
            logging.error(f"Whisper load failed: {e}")
            self.model = None
            return False

    def reload(self, model_name: str) -> bool:
        """Hot-swap the model (call from background thread)."""
        with self._lock:
            logging.info(f"Reloading model -> {model_name}")
            self.model = None
            return self.load(model_name)

    # ── Transcription ─────────────────────────────────────────────────
    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = "en",
        remove_fillers: bool = False,
        trailing_space: bool = True,
    ) -> Tuple[str, float]:
        """
        Transcribe *audio* (float32 np.ndarray, 16kHz mono).
        Returns (text, elapsed_seconds).
        """
        with self._lock:
            if self.model is None:
                logging.error("Transcriber not loaded")
                return "", 0.0

            t0 = time.perf_counter()
            try:
                lang_arg = None if (language == "auto" or not language) else language
                segments, _info = self.model.transcribe(
                    audio,
                    language=lang_arg,
                    beam_size=5,
                    vad_filter=False,              # We already ran our own VAD
                    condition_on_previous_text=False,
                )
                text = " ".join(seg.text for seg in segments).strip()

            except Exception as e:
                logging.error(f"Whisper transcription error: {e}")
                return "", 0.0

        elapsed = time.perf_counter() - t0
        logging.info(f"Transcribed {len(text.split())} words in {elapsed:.2f}s")

        if not text:
            return "", elapsed

        # ── Post-processing ────────────────────────────────────────────
        if remove_fillers:
            # 1) Remove multi-word fillers via phrase substitution
            for phrase in _FILLER_MULTI:
                text = text.replace(phrase, "")
            # 2) Remove single-word fillers
            words = text.split()
            text = " ".join(
                w for w in words
                if w.lower().rstrip(".,!?;:") not in _FILLER_SINGLE
            ).strip()
            # Clean up double-spaces left by removals
            text = re.sub(r"\s{2,}", " ", text).strip()

        if text:
            text = text[0].upper() + text[1:]   # Capitalise first char

        if trailing_space and text:
            text = text + " "

        return text, elapsed
