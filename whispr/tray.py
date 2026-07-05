"""System tray icon (pystray) with a PIL-drawn waveform glyph that
changes color with app state: idle, recording, processing, paused."""

from __future__ import annotations

from typing import Callable

from PIL import Image, ImageDraw

STATE_COLORS = {
    "idle": "#e6e6f0",
    "loading": "#8b8b99",
    "recording": "#ff6b6b",
    "processing": "#7c6cff",
    "paused": "#5a5a66",
}

_BAR_HEIGHTS = (0.35, 0.7, 1.0, 0.55, 0.8)


def draw_icon(state: str = "idle", size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, size - 2, size - 2), radius=size // 4, fill="#17171f")

    color = STATE_COLORS.get(state, STATE_COLORS["idle"])
    n = len(_BAR_HEIGHTS)
    bar_w = size // 10
    gap = (size - 16 - n * bar_w) // (n - 1)
    x = 8
    mid = size // 2
    max_h = size - 24
    for frac in _BAR_HEIGHTS:
        h = max_h * frac
        d.rounded_rectangle(
            (x, mid - h / 2, x + bar_w, mid + h / 2),
            radius=bar_w // 2, fill=color,
        )
        x += bar_w + gap
    return img


class Tray:
    def __init__(
        self,
        on_toggle_pause: Callable[[], None],
        on_settings: Callable[[], None],
        on_history: Callable[[], None],
        on_autostart_toggle: Callable[[], None],
        get_paused: Callable[[], bool],
        get_autostart: Callable[[], bool],
        on_quit: Callable[[], None],
        subtitle: str = "",
    ):
        import pystray

        self._pystray = pystray
        self._get_paused = get_paused
        self.subtitle = subtitle

        menu = pystray.Menu(
            pystray.MenuItem(lambda item: f"Whispr — {self.subtitle}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: "Resume dictation" if get_paused() else "Pause dictation",
                lambda icon, item: on_toggle_pause(),
            ),
            pystray.MenuItem("Settings…", lambda icon, item: on_settings()),
            pystray.MenuItem("History…", lambda icon, item: on_history()),
            pystray.MenuItem(
                "Start with Windows",
                lambda icon, item: on_autostart_toggle(),
                checked=lambda item: get_autostart(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Whispr", lambda icon, item: on_quit()),
        )
        self.icon = pystray.Icon("Whispr", draw_icon("loading"), "Whispr — loading model…", menu)

    def run_detached(self) -> None:
        self.icon.run_detached()

    def set_state(self, state: str, tooltip: str | None = None) -> None:
        try:
            if self._get_paused() and state == "idle":
                state = "paused"
            self.icon.icon = draw_icon(state)
            if tooltip:
                self.icon.title = tooltip
        except Exception:
            pass

    def notify(self, message: str) -> None:
        try:
            self.icon.notify(message, "Whispr")
        except Exception:
            pass

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass
