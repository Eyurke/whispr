"""Whispr main application: wires the hotkey, recorder, transcriber,
formatter, injector and UI together.

Threading model
---------------
- Tk main thread: overlay animation, settings/history windows, a 30 ms
  queue poll that applies UI state posted from other threads.
- keyboard hook thread: PTT state machine -> starts/stops the recorder
  immediately (lowest latency), then posts UI updates and STT jobs.
- worker thread: transcribe -> format -> inject -> history.
- pystray thread: tray menu; actions are posted to the Tk queue.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
import traceback

import numpy as np

from . import __version__, sounds, winutil
from .audio import AudioRecorder
from .config import Config, appdata_dir
from .formatter import format_text
from .history import History
from .history_ui import HistoryWindow
from .hotkey import Action, PTTStateMachine
from .inject import inject_text
from .listener import HotkeyListener
from .log import setup_logging
from .overlay import Overlay
from .settings_ui import SettingsWindow
from .transcriber import Transcriber
from .tray import Tray

MIN_AUDIO_SECONDS = 0.30

log = setup_logging()


class WhisprApp:
    def __init__(self):
        winutil.set_dpi_aware()
        self.cfg = Config.load()
        log.info("Whispr %s starting (model=%s, hotkey=%s)", __version__, self.cfg.model, self.cfg.hotkey)
        self.history = History(appdata_dir() / "history.db")
        self.recorder = AudioRecorder(device=self.cfg.mic_device)
        self.machine = PTTStateMachine(
            tap_ms=self.cfg.tap_ms, lock_enabled=self.cfg.tap_lock_enabled
        )
        self.paused = False
        self.model_ready = threading.Event()
        self.ui_queue: queue.Queue = queue.Queue()
        self.jobs: queue.Queue = queue.Queue()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Whispr")

        self.overlay = Overlay(self.root, level_source=lambda: self.recorder.level)
        self.settings_window: SettingsWindow | None = None
        self.history_window: HistoryWindow | None = None

        self.transcriber = Transcriber(
            self.cfg.model, self.cfg.device, self.cfg.compute_type
        )
        self.listener = HotkeyListener(self.cfg.hotkey, self.machine, self.on_action)
        self.tray = Tray(
            on_toggle_pause=lambda: self.post("toggle_pause"),
            on_settings=lambda: self.post("open_settings"),
            on_history=lambda: self.post("open_history"),
            on_autostart_toggle=lambda: self.post("toggle_autostart"),
            get_paused=lambda: self.paused,
            get_autostart=winutil.get_autostart,
            on_quit=lambda: self.post("quit"),
            subtitle=self._subtitle(),
        )

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()
        threading.Thread(target=self._warm_model, daemon=True).start()

        sounds.sound_files()  # pre-generate blips
        self.listener.start()
        self.tray.run_detached()
        self.root.after(30, self._poll)

    # ------------------------------------------------------------ helpers

    def _subtitle(self) -> str:
        return f"{self.cfg.model} · {self.transcriber.device}"

    def post(self, *message) -> None:
        self.ui_queue.put(message)

    def _warm_model(self) -> None:
        try:
            started = time.monotonic()
            self.transcriber.ensure_loaded()
            self.transcriber.transcribe(np.zeros(4800, dtype=np.float32))
            log.info("model ready: %s on %s (%.1fs)", self.transcriber.model_name,
                     self.transcriber.device, time.monotonic() - started)
        except Exception:
            log.exception("model load failed")
            self.post("notify", "Speech model failed to load. Check your connection and restart.")
            self.post("tray", "paused", "Whispr — model load failed")
            return
        self.model_ready.set()
        self.post("tray", "idle", f"Whispr — ready ({self._subtitle()})")

    # ------------------------------------------------- hotkey thread side

    def on_action(self, action: Action) -> None:
        try:
            if action == Action.START:
                self._handle_start()
            elif action == Action.STOP:
                self._handle_stop()
            elif action == Action.CANCEL:
                self._handle_cancel()
        except Exception:
            traceback.print_exc()

    def _handle_start(self) -> None:
        if self.paused:
            self.machine.escape(time.monotonic() * 1000.0)
            return
        try:
            self.recorder.start()
        except Exception:
            log.exception("microphone start failed")
            self.machine.escape(time.monotonic() * 1000.0)
            self.post("overlay", "error", "Microphone unavailable")
            return
        log.info("recording started")
        sounds.play("start", self.cfg.sounds)
        self.post("overlay", "listening")
        self.post("tray", "recording", "Whispr — listening…")

    def _handle_stop(self) -> None:
        audio = self.recorder.stop()
        sounds.play("stop", self.cfg.sounds)
        log.info("recording stopped (%.2fs audio)", audio.size / 16000.0)
        if audio.size < MIN_AUDIO_SECONDS * 16000:
            self.post("overlay", "hidden")
            self.post("tray", "idle")
            return
        self.jobs.put(("stt", audio))
        self.post("overlay", "processing")
        self.post("tray", "processing", "Whispr — transcribing…")

    def _handle_cancel(self) -> None:
        self.recorder.cancel()
        sounds.play("cancel", self.cfg.sounds)
        self.post("overlay", "hidden")
        self.post("tray", "idle")

    # ------------------------------------------------------ worker thread

    def _worker_loop(self) -> None:
        while True:
            kind, payload = self.jobs.get()
            if kind == "quit":
                return
            if kind != "stt":
                continue
            try:
                self._transcribe_and_inject(payload)
            except Exception:
                log.exception("transcription pipeline failed")
                self.post("overlay", "error", "Transcription failed")
                self.post("tray", "idle")

    def _transcribe_and_inject(self, audio: np.ndarray) -> None:
        if not self.model_ready.wait(timeout=180):
            self.post("overlay", "error", "Model still loading…")
            self.post("tray", "idle")
            return
        hotwords = ", ".join(self.cfg.dictionary) if self.cfg.dictionary else None
        started = time.monotonic()
        result = self.transcriber.transcribe(
            audio, language=self.cfg.language, hotwords=hotwords
        )
        text = format_text(result.text, self.cfg.format_options())
        log.info(
            "transcribed %.2fs audio in %.2fs -> %d chars (lang=%s)",
            audio.size / 16000.0, time.monotonic() - started, len(text), result.language,
        )
        if text.strip():
            inject_text(
                text,
                method=self.cfg.paste_method,
                restore_clipboard=self.cfg.restore_clipboard,
            )
            log.info("injected text via %s", self.cfg.paste_method)
            if self.cfg.history_enabled:
                self.history.add(text.strip(), audio.size / 16000.0)
            self.post("overlay", "done")
        else:
            self.post("overlay", "error", "Didn't catch that")
        self.post("tray", "idle", f"Whispr — ready ({self._subtitle()})")

    # ---------------------------------------------------- Tk thread side

    def _poll(self) -> None:
        try:
            while True:
                message = self.ui_queue.get_nowait()
                self._handle_ui(message)
        except queue.Empty:
            pass
        except Exception:
            traceback.print_exc()

        # reflect hands-free lock in the overlay color
        if self.machine.locked and self.overlay.state == "listening":
            self.overlay.set_state("locked")

        self.root.after(30, self._poll)

    def _handle_ui(self, message: tuple) -> None:
        kind = message[0]
        if kind == "overlay":
            state = message[1]
            text = message[2] if len(message) > 2 else None
            self.overlay.set_state(state, text)
        elif kind == "tray":
            state = message[1]
            tooltip = message[2] if len(message) > 2 else None
            self.tray.set_state(state, tooltip)
        elif kind == "notify":
            self.tray.notify(message[1])
        elif kind == "toggle_pause":
            self.paused = not self.paused
            self.tray.set_state(
                "paused" if self.paused else "idle",
                "Whispr — paused" if self.paused else f"Whispr — ready ({self._subtitle()})",
            )
        elif kind == "toggle_autostart":
            try:
                enable = not winutil.get_autostart()
                winutil.set_autostart(enable)
                self.cfg.autostart = enable
                self.cfg.save()
            except Exception:
                traceback.print_exc()
        elif kind == "open_settings":
            self._open_settings()
        elif kind == "open_history":
            self._open_history()
        elif kind == "quit":
            self.shutdown()

    def _open_settings(self) -> None:
        if self.settings_window and self.settings_window.win.winfo_exists():
            self.settings_window.win.lift()
            return
        self.settings_window = SettingsWindow(self.root, self.cfg, self.apply_settings)

    def _open_history(self) -> None:
        if self.history_window and self.history_window.win.winfo_exists():
            self.history_window.refresh()
            self.history_window.win.lift()
            return
        self.history_window = HistoryWindow(self.root, self.history)

    def apply_settings(self, cfg: Config) -> None:
        model_changed = (
            cfg.model != self.transcriber.model_name
            or cfg.device not in ("auto", self.transcriber.device)
        )
        self.cfg = cfg
        cfg.save()

        self.listener.set_combo(cfg.hotkey)
        self.machine.tap_ms = cfg.tap_ms
        self.machine.lock_enabled = cfg.tap_lock_enabled
        self.recorder.device = cfg.mic_device
        try:
            winutil.set_autostart(cfg.autostart)
        except Exception:
            traceback.print_exc()

        if model_changed:
            self.model_ready.clear()
            self.transcriber = Transcriber(cfg.model, cfg.device, cfg.compute_type)
            self.tray.subtitle = self._subtitle()
            self.post("tray", "loading", f"Whispr — loading {cfg.model}…")
            threading.Thread(target=self._warm_model, daemon=True).start()

    def shutdown(self) -> None:
        try:
            self.listener.stop()
        except Exception:
            pass
        self.jobs.put(("quit", None))
        self.tray.stop()
        try:
            self.history.close()
        except Exception:
            pass
        self.root.after(50, self.root.destroy)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if not winutil.acquire_single_instance():
        root = tk.Tk()
        root.withdraw()
        from tkinter import messagebox

        messagebox.showinfo("Whispr", "Whispr is already running — look for it in the system tray.")
        return
    WhisprApp().run()


if __name__ == "__main__":
    main()
