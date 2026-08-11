# audio.py — Microphone capture and silero-VAD processing for Lanite
import logging
import threading
import time
from collections import deque
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
CHANNELS = 1
DTYPE = "float32"
CHUNK_SIZE = 1024

# Minimum RMS considered "real" audio signal (not just noise floor)
_SIGNAL_THRESHOLD = 0.0005

# ── Waveform auto-gain (visualiser only; never affects transcription) ─────────
# Lowest loudness ceiling we'll normalise against. Prevents a silent room from
# being amplified until the noise floor fills the bars.
_AGC_FLOOR = 0.006
# Per-frame decay of the rolling peak (~30fps) — slow release so bars don't
# pump between syllables.
_AGC_DECAY = 0.995
# Below this RMS we report a flat line instead of scaled-up hiss.
_AGC_NOISE_GATE = 0.0015


def list_input_devices() -> list:
    """Return list of (index, name) for all input-capable devices."""
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            devices.append((i, d['name'], d['default_samplerate'], d['max_input_channels']))
    return devices


def _test_device_rms(index: int, duration: float = 0.8) -> float:
    """
    Open device *index* briefly and return its RMS level.
    Returns -1.0 if the device cannot be opened.
    """
    frames = []
    try:
        # Try at 16kHz first, fall back to device default
        for sr in (16000, int(sd.query_devices(index)['default_samplerate'])):
            try:
                with sd.InputStream(
                    device=index,
                    samplerate=sr,
                    channels=1,
                    dtype='float32',
                    blocksize=1024,
                    callback=lambda d, f, t, s: frames.append(d[:, 0].copy()),
                ):
                    time.sleep(duration)
                break
            except Exception:
                frames.clear()
                continue

        if not frames:
            return -1.0
        audio = np.concatenate(frames)
        return float(np.sqrt(np.mean(audio ** 2)))
    except Exception as e:
        logging.debug(f"Device {index} test failed: {e}")
        return -1.0


def find_best_device() -> Optional[int]:
    """
    Scan all input devices and return the index of the one with the
    highest RMS (i.e., most likely the active microphone).
    Returns None to use the system default if no device beats threshold.
    """
    devices = list_input_devices()
    logging.info(f"Scanning {len(devices)} input devices for active microphone…")

    best_idx  = None
    best_rms  = _SIGNAL_THRESHOLD  # must beat this floor to be selected

    # Prefer devices that have "Microphone" in the name and skip clear non-mics
    skip_keywords = ("stereo mix", "pc speaker", "output", "loopback")

    for idx, name, sr, ch in devices:
        if any(kw in name.lower() for kw in skip_keywords):
            logging.debug(f"  Skip [{idx}] {name} (loopback/output)")
            continue

        rms = _test_device_rms(idx)
        logging.info(f"  [{idx}] {name:<40s} RMS={rms:.6f}")

        if rms > best_rms:
            best_rms = rms
            best_idx = idx

    if best_idx is not None:
        name = sd.query_devices(best_idx)['name']
        logging.info(f"Best device: [{best_idx}] {name} (RMS={best_rms:.6f})")
    else:
        logging.warning("No device beat signal threshold — using system default")

    return best_idx


# ─────────────────────────────────────────────────────────────────────────────
class AudioRecorder:
    """Thread-safe mic recorder driven by a sounddevice InputStream callback."""

    def __init__(self, device_index: Optional[int] = None):
        self._recording = False
        self._chunks: list = []
        self._amplitude_buf: deque = deque(maxlen=50)
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._device_index = device_index  # None = system default
        self._device_name  = "System Default"
        # Rolling loudness ceiling for the waveform's auto-gain (see
        # get_amplitude). Starts at the quiet floor and adapts to the mic.
        self._agc_peak = _AGC_FLOOR
        self._valid = self._check_mic()

    # ── Public API ────────────────────────────────────────────────────────────
    @property
    def is_valid(self) -> bool:
        return self._valid

    @property
    def device_name(self) -> str:
        return self._device_name

    def set_device(self, index: Optional[int]):
        """Switch to a different input device (call before next start())."""
        self._device_index = index
        if index is not None:
            try:
                self._device_name = sd.query_devices(index)['name']
            except Exception:
                self._device_name = f"Device {index}"
        else:
            self._device_name = "System Default"
        logging.info(f"AudioRecorder device set to: {self._device_name}")

    def start(self) -> bool:
        """Open mic stream and begin buffering audio."""
        if not self._valid:
            logging.warning("No mic available — skipping start()")
            return False
        try:
            with self._lock:
                self._chunks = []
            # Fresh gain window per recording, and drop stale levels so the
            # first frames don't animate from the previous session's tail.
            self._amplitude_buf.clear()
            self._agc_peak = _AGC_FLOOR
            self._recording = True

            # Determine actual sample rate to use for this device
            open_sr = SAMPLE_RATE
            if self._device_index is not None:
                dev_sr = int(sd.query_devices(self._device_index)['default_samplerate'])
                if dev_sr != SAMPLE_RATE:
                    # Many BT/8kHz mics don't support 16kHz — use their native rate
                    # faster-whisper resamples internally, so this is fine
                    open_sr = dev_sr
                    logging.info(f"Device native SR={dev_sr}Hz; using that instead of 16000Hz")

            self._stream = sd.InputStream(
                device=self._device_index,
                samplerate=open_sr,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=CHUNK_SIZE,
                callback=self._callback,
            )
            self._stream.start()
            logging.debug(f"Audio stream started (device={self._device_index}, sr={open_sr})")
            return True
        except Exception as e:
            logging.error(f"Failed to start audio stream: {e}")
            self._recording = False
            return False

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return the full audio buffer as a float32 array."""
        self._recording = False
        open_sr = SAMPLE_RATE
        if self._stream:
            try:
                open_sr = int(self._stream.samplerate)
            except Exception:
                pass
            try:
                self._stream.stop()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            chunks = list(self._chunks)

        if not chunks:
            return None

        audio = np.concatenate(chunks, axis=0)

        # Resample to 16kHz if needed (Whisper requires 16kHz)
        if open_sr != SAMPLE_RATE:
            audio = _resample(audio, open_sr, SAMPLE_RATE)

        return audio

    def get_amplitude(self) -> float:
        """
        Return current mic level scaled 0→1 for the waveform animation.

        This used to be a fixed `rms * 18.0`, which assumed a hot signal.
        A quiet mic (measured RMS ~0.0086 here) only ever reached ~0.15, so
        the bars barely moved. Instead we normalise against a rolling peak:
        the loudest recent moment maps near the top of the range whatever the
        input gain, so the visualiser responds on quiet and loud mics alike.

        The peak rises instantly (so a sudden loud word doesn't clip) and
        decays slowly (so bars don't pump between syllables). It never falls
        below _AGC_FLOOR, which keeps silence looking like silence rather
        than amplifying the noise floor to full height.
        """
        if not self._amplitude_buf:
            return 0.0

        recent = list(self._amplitude_buf)[-4:]
        level = float(np.mean(recent)) if recent else 0.0

        # Track the recent loudness ceiling: attack fast, release slow.
        if level > self._agc_peak:
            self._agc_peak = level
        else:
            self._agc_peak = max(
                _AGC_FLOOR, self._agc_peak * _AGC_DECAY
            )

        # Below the noise floor, report silence outright.
        if level < _AGC_NOISE_GATE:
            return 0.0

        norm = level / self._agc_peak if self._agc_peak > 0 else 0.0
        # Gentle curve: gives small sounds visible movement without letting
        # loud ones saturate every bar flat against the ceiling.
        return float(min(1.0, norm ** 0.7))

    # ── Internal ──────────────────────────────────────────────────────────────
    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logging.debug(f"sd callback status: {status}")
        if self._recording:
            chunk = indata[:, 0].copy()
            with self._lock:
                self._chunks.append(chunk)
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            self._amplitude_buf.append(rms)

    def _check_mic(self) -> bool:
        try:
            devices = sd.query_devices()
            has_input = any(d["max_input_channels"] > 0 for d in devices)
            if not has_input:
                logging.error("No input audio devices found")
                return False
            # Update device name if index is set
            if self._device_index is not None:
                self._device_name = sd.query_devices(self._device_index)['name']
            else:
                try:
                    self._device_name = sd.query_devices(kind='input')['name']
                except Exception:
                    self._device_name = "System Default"
            return True
        except Exception as e:
            logging.error(f"Audio device query failed: {e}")
            return False


def _resample(audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    """Simple linear resampling (adequate for speech; avoids scipy dependency)."""
    if from_sr == to_sr:
        return audio
    try:
        import scipy.signal
        return scipy.signal.resample_poly(
            audio, to_sr, from_sr
        ).astype(np.float32)
    except ImportError:
        pass
    # Fallback: numpy linear interp
    duration = len(audio) / from_sr
    old_t = np.linspace(0, duration, len(audio))
    new_t = np.linspace(0, duration, int(duration * to_sr))
    return np.interp(new_t, old_t, audio).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
class VADProcessor:
    """silero-VAD wrapper — strips silence from an audio buffer."""

    MIN_SPEECH_SAMPLES = int(0.2 * SAMPLE_RATE)
    VAD_THRESHOLD = 0.30

    def __init__(self, app_dir: str):
        self._app_dir = app_dir
        self._model = None
        self._utils = None

    def load(self):
        """
        Load silero-VAD from the local cache in models/torch_hub/.

        We deliberately avoid `torch.hub.load(repo_or_dir="snakers4/silero-vad")`.
        Even with force_reload=False, that form contacts GitHub to resolve the
        branch ref before touching the cache — which cost ~27s on every startup
        and broke the offline guarantee (it hangs even longer with no network).

        Order of preference:
          1. torch.jit.load() straight off the .jit file  — no hub machinery
          2. torch.hub.load(source="local")               — local repo dir
          3. Remote hub fetch                             — first run only
        """
        import os, torch

        hub_dir = os.path.join(self._app_dir, "models", "torch_hub")
        os.makedirs(hub_dir, exist_ok=True)
        torch.hub.set_dir(hub_dir)

        local_repo = os.path.join(hub_dir, "snakers4_silero-vad_master")
        jit_path = os.path.join(
            local_repo, "src", "silero_vad", "data", "silero_vad.jit"
        )

        # ── 1. Fastest path: load the TorchScript model directly ──────────
        if os.path.isfile(jit_path):
            try:
                model = torch.jit.load(jit_path, map_location="cpu")
                model.eval()
                self._model = model
                self._utils = self._local_utils(local_repo)
                logging.info("silero-VAD loaded from local .jit (offline)")
                return
            except Exception as e:
                logging.warning(f"Direct .jit load failed ({e}) — trying local hub")

        # ── 2. Local hub repo (still fully offline) ───────────────────────
        if os.path.isdir(local_repo):
            try:
                self._model, self._utils = torch.hub.load(
                    repo_or_dir=local_repo,
                    model="silero_vad",
                    source="local",
                    onnx=False,
                    verbose=False,
                )
                logging.info("silero-VAD loaded from local hub cache (offline)")
                return
            except Exception as e:
                logging.warning(f"Local hub load failed ({e}) — falling back to remote")

        # ── 3. Remote fetch — first run only, requires network ────────────
        try:
            logging.info("silero-VAD not cached locally — fetching from GitHub…")
            self._model, self._utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                verbose=False,
            )
            logging.info("silero-VAD loaded (remote)")
        except Exception as e:
            logging.error(f"silero-VAD load failed: {e}")
            self._model = None

    @staticmethod
    def _local_utils(local_repo: str):
        """
        Import silero's utils_vad helpers from the cached repo without going
        through torch.hub. Returns the same 5-tuple hubconf.py builds, so
        process() can keep using self._utils[0] (get_speech_timestamps).
        """
        import os, sys

        src = os.path.join(local_repo, "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from silero_vad.utils_vad import (
            get_speech_timestamps,
            save_audio,
            read_audio,
            VADIterator,
            collect_chunks,
        )
        return (
            get_speech_timestamps,
            save_audio,
            read_audio,
            VADIterator,
            collect_chunks,
        )

    def process(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """
        Run VAD, return speech-only segment.
        Returns None if audio is too short or contains no speech.
        Falls back to returning the original audio if VAD model failed to load.
        """
        duration_s = len(audio) / SAMPLE_RATE if len(audio) > 0 else 0
        rms  = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        peak = float(np.max(np.abs(audio)))         if len(audio) > 0 else 0.0
        logging.info(
            f"VAD input: {len(audio)} samples ({duration_s:.2f}s), "
            f"RMS={rms:.5f}, peak={peak:.5f}"
        )

        if len(audio) < self.MIN_SPEECH_SAMPLES:
            logging.info(f"VAD: audio too short ({len(audio)} samples, need {self.MIN_SPEECH_SAMPLES})")
            return None

        # No VAD model — accept audio that has detectable signal
        if self._model is None:
            logging.warning("VAD model not loaded — using raw audio (RMS check)")
            if rms < 0.001:
                logging.info("VAD fallback: RMS too low — discarding")
                return None
            return audio

        try:
            import torch
            get_speech_timestamps = self._utils[0]

            tensor = torch.FloatTensor(audio)
            timestamps = get_speech_timestamps(
                tensor,
                self._model,
                sampling_rate=SAMPLE_RATE,
                min_speech_duration_ms=150,
                min_silence_duration_ms=100,
                threshold=self.VAD_THRESHOLD,
            )

            logging.info(f"VAD timestamps found: {len(timestamps)}")

            if not timestamps:
                # Safety net: if RMS is non-trivial, pass raw audio to Whisper
                if rms >= 0.005:
                    logging.info(
                        f"VAD found no timestamps but RMS={rms:.5f} is non-trivial "
                        "-> passing raw audio to Whisper anyway"
                    )
                    return audio
                logging.info("VAD: no speech detected (low signal)")
                return None

            total_samp = sum(ts["end"] - ts["start"] for ts in timestamps)
            if total_samp < self.MIN_SPEECH_SAMPLES:
                logging.info(f"VAD: speech segments too short ({total_samp} samp)")
                return None

            segments = [audio[ts["start"]: ts["end"]] for ts in timestamps]
            result = np.concatenate(segments)
            logging.info(f"VAD: kept {len(result)} samples ({len(result)/SAMPLE_RATE:.2f}s)")
            return result

        except Exception as e:
            logging.error(f"VAD processing error: {e}")
            return audio if len(audio) >= self.MIN_SPEECH_SAMPLES else None
