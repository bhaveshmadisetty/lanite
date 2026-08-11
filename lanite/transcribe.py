# transcribe.py — faster-whisper wrapper for Lanite
import logging
import os
import re
import threading
import time
from typing import Optional, Tuple

import numpy as np

# Single-word fillers — ONLY true disfluencies that are never content words.
#
# Previously this also contained: like, so, basically, literally, actually,
# right, okay. Those are ordinary English words, and stripping them silently
# corrupted correct transcriptions:
#     "Turn right at the next light" -> "Turn at the next light"
#     "I like this design so much"   -> "I this design much"
# That looked like bad transcription accuracy, but Whisper was right and this
# post-processing was deleting real words. Keep this list conservative.
_FILLER_SINGLE = frozenset({
    "um", "uh", "umm", "uhh", "hmm", "hm", "mhm", "erm", "eh",
})
# Multi-word fillers removed via phrase substitution before word-split.
# Matched case-insensitively on word boundaries so "you know" doesn't also
# clobber "do you know where it is".
_FILLER_MULTI = ["you know what i mean", "i mean like"]

# Whisper emits these on silence/near-silence — a well-documented artifact of
# the training data (subtitle corpora). Stress testing produced "You" from both
# pure silence and a 0.1s clip. If the ENTIRE transcript is just one of these,
# it's a hallucination, not speech, so we drop it rather than paste it into
# whatever the user was typing in.
_HALLUCINATIONS = frozenset({
    "you", "thank you", "thanks for watching", "thank you for watching",
    "bye", "bye.", ".", "so", "okay", "oh",
    "please subscribe", "subtitles by the amara.org community",
})


class Transcriber:
    """
    Wraps faster-whisper WhisperModel.

    - Model is loaded *once* at startup and kept in RAM.
    - On CPU with int8: ~2-3s for 10s of speech.
    - Returns (text, elapsed_seconds) tuple.
    """

    def __init__(self, models_dir: str, compute_type: str = "int8",
                 beam_size: int = 1):
        self.models_dir = models_dir
        self.model = None
        self._current_model_name: Optional[str] = None
        self._compute_type = compute_type
        self._beam_size = max(1, int(beam_size))
        self._lock = threading.Lock()

    # ── Loading ───────────────────────────────────────────────────────
    def _find_local_snapshot(self, model_name: str) -> Optional[str]:
        """
        Resolve an already-downloaded model directory.

        faster-whisper caches via HuggingFace, so the on-disk layout is
            models--Systran--faster-whisper-<name>/snapshots/<hash>/
        NOT the flat models/<name>/ this used to look for. That mismatch meant
        the local check always missed and every launch re-entered the HF hub
        resolver — the "Downloading Whisper model ..." line in the log for a
        model that was already on disk.

        Returns the snapshot path containing model.bin, or None.
        """
        # Flat layout (manually placed models) — still honoured.
        flat = os.path.join(self.models_dir, model_name)
        if os.path.isdir(flat) and os.path.isfile(os.path.join(flat, "model.bin")):
            return flat

        # HuggingFace cache layout.
        hf_dir = os.path.join(
            self.models_dir, f"models--Systran--faster-whisper-{model_name}"
        )
        snapshots = os.path.join(hf_dir, "snapshots")
        if not os.path.isdir(snapshots):
            return None

        for entry in sorted(os.listdir(snapshots)):
            candidate = os.path.join(snapshots, entry)
            if os.path.isfile(os.path.join(candidate, "model.bin")):
                return candidate
        return None

    def load(self, model_name: str = "small.en") -> bool:
        self._current_model_name = model_name
        try:
            from faster_whisper import WhisperModel

            local_path = self._find_local_snapshot(model_name)
            if local_path:
                model_arg = local_path
                logging.info(f"Loading Whisper from local cache: {local_path}")
            else:
                model_arg = model_name      # faster-whisper will download
                logging.info(f"Downloading Whisper model '{model_name}' -> {self.models_dir}")

            self.model = WhisperModel(
                model_size_or_path=model_arg,
                device="cpu",
                compute_type=self._compute_type,
                download_root=self.models_dir,
                num_workers=1,
                # When we resolved a local snapshot, never round-trip to HF.
                local_files_only=bool(local_path),
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
                # beam_size=1 (greedy) measured ~1.5x faster than beam_size=5
                # on this machine (2.40s -> 1.63s for 3s of audio) with no
                # observed quality loss on short dictation. Configurable via
                # the "beam_size" setting if you ever want the old behaviour.
                segments, _info = self.model.transcribe(
                    audio,
                    language=lang_arg,
                    beam_size=self._beam_size,
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

        # Drop whole-transcript hallucinations (Whisper's silence artifacts).
        # Only when the ENTIRE output is one of them — a real sentence that
        # merely contains "you" is untouched.
        if text.strip().lower().rstrip(".!?,") in _HALLUCINATIONS:
            logging.info(f"Discarding likely hallucination: {text!r}")
            return "", elapsed

        # ── Post-processing ────────────────────────────────────────────
        if remove_fillers:
            # 1) Multi-word fillers — case-insensitive, whole-phrase only.
            #    (str.replace was case-sensitive and matched mid-word.)
            for phrase in _FILLER_MULTI:
                text = re.sub(
                    r"\b" + re.escape(phrase) + r"\b", "", text,
                    flags=re.IGNORECASE,
                )
            # 2) Single-word fillers
            words = text.split()
            text = " ".join(
                w for w in words
                if w.lower().rstrip(".,!?;:") not in _FILLER_SINGLE
            ).strip()
            # Tidy up spacing/punctuation left behind by removals
            text = re.sub(r"\s{2,}", " ", text)
            text = re.sub(r"\s+([,.!?;:])", r"\1", text).strip()

        if text:
            text = text[0].upper() + text[1:]   # Capitalise first char

        if trailing_space and text:
            text = text + " "

        return text, elapsed
