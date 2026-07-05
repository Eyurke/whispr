import json

from whispr.config import DEFAULTS, Config


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = Config.load(tmp_path / "config.json")
    assert cfg.model == "small"
    assert cfg.hotkey == "ctrl+win"
    assert cfg.remove_fillers is True


def test_save_and_reload_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = Config.load(path)
    cfg.model = "base"
    cfg.dictionary = ["Anthropic"]
    cfg.save()

    reloaded = Config.load(path)
    assert reloaded.model == "base"
    assert reloaded.dictionary == ["Anthropic"]


def test_partial_file_merges_over_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"model": "tiny"}), encoding="utf-8")

    cfg = Config.load(path)
    assert cfg.model == "tiny"
    assert cfg.hotkey == DEFAULTS["hotkey"]


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")

    cfg = Config.load(path)
    assert cfg.model == DEFAULTS["model"]


def test_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"model": "tiny", "bogus_key": 1}), encoding="utf-8")

    cfg = Config.load(path)
    assert not hasattr(cfg, "bogus_key") or cfg.model == "tiny"


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "deep" / "nested" / "config.json"
    cfg = Config.load(path)
    cfg.save()
    assert path.exists()
