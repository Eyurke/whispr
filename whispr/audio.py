"""Microphone capture via sounddevice (PortAudio).

We ask for 16 kHz mono float32 directly (the MME host API resamples for
us); if the device refuses, we capture at its native rate and resample
with linear interpolation - plenty for speech models.
"""

from __future__ import annotations

import threading

import numpy as np

TARGET_SR = 16000


def resample_to_16k(audio: np.ndarray, src_sr: int) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32)
    if src_sr == TARGET_SR or audio.size == 0:
        return audio.astype(np.float32)
    n_out = int(round(audio.size * TARGET_SR / src_sr))
    if n_out <= 0:
        return np.zeros(0, dtype=np.float32)
    x_old = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def list_input_devices() -> list[tuple[int | None, str]]:
    """(device_index, name) pairs; None means system default."""
    import sounddevice as sd

    devices: list[tuple[int | None, str]] = [(None, "System default")]
    try:
        default_in = sd.default.device[0]
        hostapi = sd.query_devices(default_in)["hostapi"] if default_in is not None and default_in >= 0 else 0
    except Exception:
        hostapi = 0
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0 and dev.get("hostapi") == hostapi:
                devices.append((idx, dev["name"]))
    except Exception:
        pass
    return devices


class AudioRecorder:
    """Start/stop capture; returns float32 mono 16 kHz. Thread-safe enough
    for one recorder driven by the hotkey thread."""

    def __init__(self, device: int | None = None):
        self.device = device
        self._frames: list[np.ndarray] = []
        self._stream = None
        self._sr = TARGET_SR
        self._level = 0.0
        self._lock = threading.Lock()

    @property
    def level(self) -> float:
        """Smoothed RMS of the latest audio, for the overlay meter."""
        return self._level

    @property
    def active(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, _frames, _time_info, _status):
        block = indata[:, 0].copy()
        with self._lock:
            self._frames.append(block)
        rms = float(np.sqrt(np.mean(block * block))) if block.size else 0.0
        self._level = max(rms, self._level * 0.6)

    def start(self) -> None:
        import sounddevice as sd

        if self._stream is not None:
            return
        with self._lock:
            self._frames = []
        self._level = 0.0
        try:
            stream = sd.InputStream(
                samplerate=TARGET_SR, channels=1, dtype="float32",
                device=self.device, callback=self._callback,
            )
            stream.start()
            self._sr = TARGET_SR
        except Exception:
            info = sd.query_devices(self.device, "input")
            native_sr = int(info["default_samplerate"])
            stream = sd.InputStream(
                samplerate=native_sr, channels=1, dtype="float32",
                device=self.device, callback=self._callback,
            )
            stream.start()
            self._sr = native_sr
        self._stream = stream

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    def stop(self) -> np.ndarray:
        self._close_stream()
        with self._lock:
            frames, self._frames = self._frames, []
        self._level = 0.0
        if not frames:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(frames)
        return resample_to_16k(audio, self._sr)

    def cancel(self) -> None:
        self._close_stream()
        with self._lock:
            self._frames = []
        self._level = 0.0
