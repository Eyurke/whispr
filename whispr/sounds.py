"""Soft start/stop/cancel blips (generated once, played with winsound)."""

from __future__ import annotations

import math
import wave
from pathlib import Path

from .config import appdata_dir

_SR = 44100
_AMP = 0.16

_SPECS = {
    # name: list of (freq_hz, duration_s)
    "start": [(660.0, 0.07), (880.0, 0.09)],
    "stop": [(880.0, 0.07), (660.0, 0.09)],
    "cancel": [(330.0, 0.12)],
}


def _render(segments: list[tuple[float, float]]) -> bytes:
    samples: list[int] = []
    for freq, dur in segments:
        n = int(_SR * dur)
        fade = max(1, int(_SR * 0.008))
        for i in range(n):
            envelope = 1.0
            if i < fade:
                envelope = i / fade
            elif i > n - fade:
                envelope = max(0.0, (n - i) / fade)
            value = _AMP * envelope * math.sin(2.0 * math.pi * freq * i / _SR)
            samples.append(int(value * 32767))
    return b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples)


def sound_files() -> dict[str, Path]:
    folder = appdata_dir() / "sounds"
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, spec in _SPECS.items():
        path = folder / f"{name}.wav"
        if not path.exists():
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(_SR)
                w.writeframes(_render(spec))
        paths[name] = path
    return paths


def play(kind: str, enabled: bool = True) -> None:
    if not enabled:
        return
    try:
        import winsound

        path = sound_files().get(kind)
        if path:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass
