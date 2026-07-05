"""OS adapter: feeds real keyboard events into the PTT state machine.

Uses the `keyboard` package's low-level hook so hold/release of modifier
combos (e.g. Ctrl+Win) is seen even while other apps have focus.

Two modes:
- "hold":   press starts recording, release stops (quick tap locks).
- "toggle": one clean tap starts, the next clean tap stops. A tap only
  counts if no other key was pressed while the hotkey was down, so
  Alt+Tab / Alt+F4 style shortcuts never trigger dictation.
"""

from __future__ import annotations

import time
from typing import Callable

from .hotkey import Action, PTTStateMachine

_ALIASES: dict[str, set[str]] = {
    "ctrl": {"ctrl", "left ctrl", "right ctrl"},
    "control": {"ctrl", "left ctrl", "right ctrl"},
    # the `keyboard` package reports left-side modifiers with the bare name
    "left ctrl": {"ctrl", "left ctrl"},
    "right ctrl": {"right ctrl"},
    "win": {"windows", "left windows", "right windows"},
    "windows": {"windows", "left windows", "right windows"},
    "meta": {"windows", "left windows", "right windows"},
    "left win": {"windows", "left windows"},
    "left windows": {"windows", "left windows"},
    "right win": {"right windows"},
    "right windows": {"right windows"},
    "alt": {"alt", "left alt", "right alt", "alt gr"},
    "left alt": {"alt", "left alt"},
    "right alt": {"right alt", "alt gr"},
    "shift": {"shift", "left shift", "right shift"},
    "left shift": {"shift", "left shift"},
    "right shift": {"right shift"},
}

_ALT_NAMES = {"alt", "left alt", "right alt", "alt gr"}


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
        mode: str = "hold",
    ):
        self.machine = machine
        self.on_action = on_action
        self.mode = mode
        self._groups = parse_combo(combo)
        self._down: set[str] = set()
        self._active = False        # combo currently satisfied
        self._other_seen = False    # a non-combo key was pressed while active
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
        self._other_seen = False

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._down.clear()
        self._active = False
        self._other_seen = False

    def _combo_has_alt(self) -> bool:
        return any(group & _ALT_NAMES for group in self._groups)

    def _cancel_alt_menu(self) -> None:
        """A bare Alt tap puts many apps into menu-bar mode; a lone Ctrl
        tap cancels that without any other side effect."""
        try:
            from .inject import KEYEVENTF_KEYUP, VK_CONTROL, _key_input, _send

            _send([
                _key_input(vk=VK_CONTROL),
                _key_input(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP),
            ])
        except Exception:
            pass

    def _on_event(self, event) -> None:
        try:
            name = (event.name or "").lower()
            now_ms = time.monotonic() * 1000.0

            if name in ("esc", "escape"):
                if event.event_type == "down":
                    if self._active:
                        self._other_seen = True
                    if self.machine.recording:
                        self._dispatch(self.machine.escape(now_ms))
                return

            if not self._groups:
                return
            flat = set().union(*self._groups)

            if name not in flat:
                if event.event_type == "down" and self._active:
                    self._other_seen = True  # combo is part of a shortcut chord
                return

            if event.event_type == "down":
                self._down.add(name)
            else:
                self._down.discard(name)

            satisfied = all(self._down & group for group in self._groups)
            if satisfied == self._active:
                return
            self._active = satisfied

            if self.mode == "toggle":
                if satisfied:
                    self._other_seen = False
                elif not self._other_seen:
                    self._dispatch(self.machine.toggle_tap(now_ms))
                    if self._combo_has_alt():
                        self._cancel_alt_menu()
            else:  # hold mode
                if satisfied:
                    self._dispatch(self.machine.combo_down(now_ms))
                else:
                    self._dispatch(self.machine.combo_up(now_ms))
        except Exception:
            pass  # a hook exception would kill all keyboard handling

    def _dispatch(self, action: Action) -> None:
        if action != Action.NONE:
            self.on_action(action)
