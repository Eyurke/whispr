"""Configuration: JSON file in %APPDATA%/Whispr, merged over defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS: dict = {
    "hotkey": "ctrl+win",
    "tap_lock_enabled": True,
    "tap_ms": 280,
    "model": "small",
    "device": "auto",
    "compute_type": "auto",
    "language": "auto",
    "mic_device": None,
    "paste_method": "paste",
    "restore_clipboard": True,
    "remove_fillers": True,
    "capitalize_sentences": True,
    "trailing_space": True,
    "spoken_commands": False,
    "dictionary": [],
    "replacements": {},
    "sounds": True,
    "history_enabled": True,
    "autostart": False,
}


def appdata_dir() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home())
    return Path(root) / "Whispr"


def default_config_path() -> Path:
    return appdata_dir() / "config.json"


class Config:
    """Attribute-style access to settings; only keys in DEFAULTS exist."""

    def __init__(self, data: dict | None = None, path: Path | None = None):
        self._path = Path(path) if path else default_config_path()
        merged = dict(DEFAULTS)
        for key, value in (data or {}).items():
            if key in DEFAULTS:
                merged[key] = value
        self.__dict__.update(merged)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        p = Path(path) if path else default_config_path()
        data: dict = {}
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            data = {}
        return cls(data, p)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: getattr(self, key) for key in DEFAULTS}
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    def format_options(self):
        from .formatter import FormatOptions

        return FormatOptions(
            remove_fillers=self.remove_fillers,
            capitalize_sentences=self.capitalize_sentences,
            trailing_space=self.trailing_space,
            spoken_commands=self.spoken_commands,
            dictionary=tuple(self.dictionary or ()),
            replacements=dict(self.replacements or {}),
        )
