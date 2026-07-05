import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from whispr.transcriber import Transcriber, resolve_backend


def test_resolve_backend_explicit_passthrough():
    assert resolve_backend("cpu", "int8") == ("cpu", "int8")


def test_resolve_backend_auto_cpu_uses_int8(monkeypatch):
    import whispr.transcriber as t

    monkeypatch.setattr(t, "_cuda_available", lambda: False)
    assert resolve_backend("auto", "auto") == ("cpu", "int8")


def test_resolve_backend_auto_cuda_uses_float16(monkeypatch):
    import whispr.transcriber as t

    monkeypatch.setattr(t, "_cuda_available", lambda: True)
    assert resolve_backend("auto", "auto") == ("cuda", "float16")


def _synthesize_speech(path: Path, text: str) -> None:
    """Generate a 16 kHz mono WAV using the Windows built-in TTS voice."""
    script = f"""
Add-Type -AssemblyName System.Speech
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile('{path}', $fmt)
$s.Rate = -1
$s.Speak('{text}')
$s.Dispose()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
        timeout=60,
    )


@pytest.mark.e2e
def test_transcribes_synthesized_speech(tmp_path):
    wav_path = tmp_path / "fox.wav"
    _synthesize_speech(wav_path, "The quick brown fox jumps over the lazy dog.")

    with wave.open(str(wav_path), "rb") as w:
        assert w.getframerate() == 16000
        frames = w.readframes(w.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    engine = Transcriber(model_name="tiny", device="cpu", compute_type="int8")
    result = engine.transcribe(audio, language="en")

    normalized = result.text.lower()
    assert "quick brown fox" in normalized
    assert result.duration_s > 1.0
