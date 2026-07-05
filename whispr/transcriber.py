"""Local speech-to-text via faster-whisper (CTranslate2).

Runs fully offline after the first model download. On CPU we use int8
quantization (fast on modern desktops); with an NVIDIA GPU present,
float16 on CUDA is picked automatically.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from .config import appdata_dir


@dataclass
class TranscriptResult:
    text: str
    language: str | None
    duration_s: float


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def resolve_backend(device: str, compute_type: str) -> tuple[str, str]:
    """Map 'auto' to the best available (device, compute_type) pair."""
    dev = device
    if dev in (None, "", "auto"):
        dev = "cuda" if _cuda_available() else "cpu"
    ct = compute_type
    if ct in (None, "", "auto"):
        ct = "float16" if dev == "cuda" else "int8"
    return dev, ct


def models_dir() -> Path:
    return appdata_dir() / "models"


class Transcriber:
    """Lazy-loading wrapper around faster_whisper.WhisperModel (thread-safe)."""

    def __init__(
        self,
        model_name: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        download_root: Path | None = None,
    ):
        self.model_name = model_name
        self.device, self.compute_type = resolve_backend(device, compute_type)
        self.download_root = Path(download_root) if download_root else models_dir()
        self._model = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self.download_root.mkdir(parents=True, exist_ok=True)
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(self.download_root),
                )

    def transcribe(
        self,
        audio,
        language: str | None = None,
        hotwords: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptResult:
        """Transcribe float32 mono 16 kHz audio (numpy array) or a file path."""
        self.ensure_loaded()
        lang = None if language in (None, "", "auto") else language
        segments, info = self._model.transcribe(
            audio,
            language=lang,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            hotwords=hotwords or None,
            initial_prompt=initial_prompt or None,
        )
        text = "".join(segment.text for segment in segments).strip()
        return TranscriptResult(text=text, language=info.language, duration_s=info.duration)
