import numpy as np

from whispr.audio import resample_to_16k


def test_resample_noop_at_16k():
    audio = np.linspace(-1, 1, 16000, dtype=np.float32)
    out = resample_to_16k(audio, 16000)
    assert out.dtype == np.float32
    assert len(out) == 16000
    assert np.allclose(out, audio)


def test_resample_48k_to_16k_length_and_shape():
    audio = np.sin(np.linspace(0, 2 * np.pi * 220, 48000)).astype(np.float32)
    out = resample_to_16k(audio, 48000)
    assert out.dtype == np.float32
    assert len(out) == 16000


def test_resample_preserves_ramp_values():
    ramp = np.linspace(0.0, 1.0, 48000, dtype=np.float32)
    out = resample_to_16k(ramp, 48000)
    expected = np.linspace(0.0, 1.0, 16000, endpoint=False, dtype=np.float32)
    assert np.allclose(out, expected, atol=1e-3)


def test_resample_empty_input():
    out = resample_to_16k(np.zeros(0, dtype=np.float32), 48000)
    assert len(out) == 0
    assert out.dtype == np.float32
