"""Settings window (tkinter/ttk)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .audio import list_input_devices
from .config import Config

HOTKEY_CHOICES = ["ctrl+win", "ctrl+alt", "alt+win", "ctrl+shift", "f8", "f9", "scroll lock"]
MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3", "distil-large-v3"]
MODEL_HINT = "tiny/base = fastest · small = best balance · large-v3 = best accuracy (slower)"
LANGUAGE_CHOICES = ["auto", "en", "ru", "uk", "de", "es", "fr", "it", "pt", "pl", "nl", "ja", "zh", "ko"]


def _parse_replacements(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in raw.splitlines():
        if "->" in line:
            src, _, dst = line.partition("->")
            src, dst = src.strip(), dst.strip()
            if src and dst:
                out[src] = dst
    return out


class SettingsWindow:
    def __init__(self, root: tk.Tk, cfg: Config, on_apply):
        self.cfg = cfg
        self.on_apply = on_apply

        self.win = tk.Toplevel(root)
        self.win.title("Whispr Settings")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        pad = {"padx": 10, "pady": 4}
        body = ttk.Frame(self.win, padding=12)
        body.pack(fill="both", expand=True)

        # --- Dictation -------------------------------------------------
        dict_frame = ttk.LabelFrame(body, text="Dictation", padding=8)
        dict_frame.pack(fill="x", **pad)

        ttk.Label(dict_frame, text="Hold-to-talk hotkey:").grid(row=0, column=0, sticky="w")
        self.hotkey_var = tk.StringVar(value=cfg.hotkey)
        ttk.Combobox(dict_frame, textvariable=self.hotkey_var, values=HOTKEY_CHOICES, width=18).grid(row=0, column=1, sticky="w", padx=8)

        self.tap_lock_var = tk.BooleanVar(value=cfg.tap_lock_enabled)
        ttk.Checkbutton(
            dict_frame, text="Quick tap locks hands-free recording (tap again to stop)",
            variable=self.tap_lock_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(dict_frame, text="Microphone:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._devices = list_input_devices()
        device_names = [name for _idx, name in self._devices]
        current = next((name for idx, name in self._devices if idx == cfg.mic_device), device_names[0])
        self.mic_var = tk.StringVar(value=current)
        ttk.Combobox(dict_frame, textvariable=self.mic_var, values=device_names, width=38, state="readonly").grid(row=2, column=1, sticky="w", padx=8, pady=(6, 0))

        ttk.Label(dict_frame, text="Language:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.lang_var = tk.StringVar(value=cfg.language)
        ttk.Combobox(dict_frame, textvariable=self.lang_var, values=LANGUAGE_CHOICES, width=18).grid(row=3, column=1, sticky="w", padx=8, pady=(6, 0))

        # --- Model -----------------------------------------------------
        model_frame = ttk.LabelFrame(body, text="Speech model (runs locally)", padding=8)
        model_frame.pack(fill="x", **pad)
        ttk.Label(model_frame, text="Whisper model:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(value=cfg.model)
        ttk.Combobox(model_frame, textvariable=self.model_var, values=MODEL_CHOICES, width=18).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(model_frame, text=MODEL_HINT, foreground="#666").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # --- Text ------------------------------------------------------
        text_frame = ttk.LabelFrame(body, text="Text cleanup", padding=8)
        text_frame.pack(fill="x", **pad)
        self.fillers_var = tk.BooleanVar(value=cfg.remove_fillers)
        self.caps_var = tk.BooleanVar(value=cfg.capitalize_sentences)
        self.space_var = tk.BooleanVar(value=cfg.trailing_space)
        self.commands_var = tk.BooleanVar(value=cfg.spoken_commands)
        ttk.Checkbutton(text_frame, text="Remove filler words (um, uh, hmm…)", variable=self.fillers_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(text_frame, text="Capitalize sentences", variable=self.caps_var).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(text_frame, text="Append trailing space (chain dictations)", variable=self.space_var).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(text_frame, text='Spoken commands ("new line", "new paragraph")', variable=self.commands_var).grid(row=3, column=0, sticky="w")

        ttk.Label(text_frame, text="Dictionary (names/terms to spell correctly, one per line):").grid(row=4, column=0, sticky="w", pady=(8, 2))
        self.dict_text = tk.Text(text_frame, width=48, height=4, font=("Segoe UI", 9))
        self.dict_text.grid(row=5, column=0, sticky="we")
        self.dict_text.insert("1.0", "\n".join(cfg.dictionary or []))

        ttk.Label(text_frame, text="Replacements (one per line, e.g.  gonna -> going to):").grid(row=6, column=0, sticky="w", pady=(8, 2))
        self.repl_text = tk.Text(text_frame, width=48, height=4, font=("Segoe UI", 9))
        self.repl_text.grid(row=7, column=0, sticky="we")
        self.repl_text.insert("1.0", "\n".join(f"{k} -> {v}" for k, v in (cfg.replacements or {}).items()))

        # --- System ----------------------------------------------------
        sys_frame = ttk.LabelFrame(body, text="System", padding=8)
        sys_frame.pack(fill="x", **pad)
        self.paste_var = tk.StringVar(value=cfg.paste_method)
        ttk.Label(sys_frame, text="Insert text by:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(sys_frame, text="Paste (fast, recommended)", variable=self.paste_var, value="paste").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(sys_frame, text="Typing (compatible)", variable=self.paste_var, value="type").grid(row=0, column=2, sticky="w")

        self.restore_var = tk.BooleanVar(value=cfg.restore_clipboard)
        self.sounds_var = tk.BooleanVar(value=cfg.sounds)
        self.autostart_var = tk.BooleanVar(value=cfg.autostart)
        self.history_var = tk.BooleanVar(value=cfg.history_enabled)
        ttk.Checkbutton(sys_frame, text="Restore clipboard after paste", variable=self.restore_var).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(sys_frame, text="Play start/stop sounds", variable=self.sounds_var).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(sys_frame, text="Save dictation history", variable=self.history_var).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(sys_frame, text="Start Whispr with Windows", variable=self.autostart_var).grid(row=4, column=0, columnspan=2, sticky="w")

        # --- Buttons ---------------------------------------------------
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Save && Apply", command=self._save).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Cancel", command=self.win.destroy).pack(side="right")

    def _save(self) -> None:
        hotkey = self.hotkey_var.get().strip().lower()
        if not hotkey:
            messagebox.showerror("Whispr", "Hotkey cannot be empty.", parent=self.win)
            return
        self.cfg.hotkey = hotkey
        self.cfg.tap_lock_enabled = self.tap_lock_var.get()
        self.cfg.language = self.lang_var.get().strip() or "auto"
        self.cfg.model = self.model_var.get().strip() or "small"
        self.cfg.mic_device = next(
            (idx for idx, name in self._devices if name == self.mic_var.get()), None
        )
        self.cfg.remove_fillers = self.fillers_var.get()
        self.cfg.capitalize_sentences = self.caps_var.get()
        self.cfg.trailing_space = self.space_var.get()
        self.cfg.spoken_commands = self.commands_var.get()
        self.cfg.dictionary = [
            line.strip() for line in self.dict_text.get("1.0", "end").splitlines() if line.strip()
        ]
        self.cfg.replacements = _parse_replacements(self.repl_text.get("1.0", "end"))
        self.cfg.paste_method = self.paste_var.get()
        self.cfg.restore_clipboard = self.restore_var.get()
        self.cfg.sounds = self.sounds_var.get()
        self.cfg.history_enabled = self.history_var.get()
        self.cfg.autostart = self.autostart_var.get()

        self.on_apply(self.cfg)
        self.win.destroy()
