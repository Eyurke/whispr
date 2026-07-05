"""OS adapter: feeds real keyboard events into the PTT state machine.

Uses the `keyboard` package's low-level hook so hold/release of modifier
combos (e.g. Ctrl+Win) is seen even while other apps have focus.
"""

from __future__ import annotations

import time
from typing import Callable

from .hotkey import Action, PTTStateMachine

_ALIASES: dict[str, set[str]] = {
    "ctrl": {"ctrl", "left ctrl", "right ctrl"},
    "control": {"ctrl", "left ctrl", "right ctrl"},
    "win": {"windows", "left windows", "right windows"},
    "windows": {"windows", "left windows", "right windows"},
    "meta": {"windows", "left windows", "right windows"},
    "alt": {"alt", "left alt", "right alt", "alt gr"},
    "shift": {"shift", "left shift", "right shift"},
}


def parse_combo(combo: str) -> list[frozenset[str]]:
    """'ctrl+win' -> groups of acceptable key names, one group per part."""
    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    return [frozenset(_ALIASES.get(p, {p})) for p in parts]


class HotkeyListener:
    def __init__(
        self,
        combo: str,
        machine: PTTStateMachine,
        on_action: Callable[[Action], None],
    ):
        self.machine = machine
        self.on_action = on_action
        self._groups = parse_combo(combo)
        self._down: set[str] = set()
        self._active = False
        self._hook = None

    def start(self) -> None:
        import keyboard

        if self._hook is None:
            self._hook = keyboard.hook(self._on_event)

    def stop(self) -> None:
        import keyboard

        if self._hook is not None:
            try:
                keyboard.unhook(self._hook)
            except Exception:
                pass
            self._hook = None

    def set_combo(self, combo: str) -> None:
        self._groups = parse_combo(combo)
        self._down.clear()
        self._active = False

    def _on_event(self, event) -> None:
        try:
            name = (event.name or "").lower()
            now_ms = time.monotonic() * 1000.0

            if name in ("esc", "escape"):
                if event.event_type == "down" and self.machine.recording:
                    self._dispatch(self.machine.escape(now_ms))
                return

            if not self._groups:
                return
            flat = set().union(*self._groups)
            if name not in flat:
                return

            if event.event_type == "down":
                self._down.add(name)
            else:
                self._down.discard(name)

            satisfied = all(self._down & group for group in self._groups)
            if satisfied != self._active:
                self._active = satisfied
                if satisfied:
                    self._dispatch(self.machine.combo_down(now_ms))
                else:
                    self._dispatch(self.machine.combo_up(now_ms))
        except Exception:
            pass  # a hook exception would kill all keyboard handling

    def _dispatch(self, action: Action) -> None:
        if action != Action.NONE:
            self.on_action(action)
