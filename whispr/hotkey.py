"""Push-to-talk hotkey handling.

PTTStateMachine is a pure state machine (testable without a keyboard):
hold the combo to talk, release to commit; a quick tap locks hands-free
recording until the next tap; Escape cancels.

The OS adapter that feeds it real key events lives in listener.py.
"""

from __future__ import annotations

from enum import Enum


class Action(Enum):
    NONE = "none"
    START = "start"
    STOP = "stop"
    CANCEL = "cancel"


class _State(Enum):
    IDLE = "idle"
    PRESSED = "pressed"   # combo held, recording (push-to-talk)
    LOCKED = "locked"     # combo released after a quick tap, still recording


class PTTStateMachine:
    def __init__(self, tap_ms: int = 280, lock_enabled: bool = True):
        self.tap_ms = tap_ms
        self.lock_enabled = lock_enabled
        self._state = _State.IDLE
        self._t0 = 0.0
        self._swallow_up = False  # ignore the release of a press we already acted on

    @property
    def recording(self) -> bool:
        return self._state in (_State.PRESSED, _State.LOCKED)

    @property
    def locked(self) -> bool:
        return self._state == _State.LOCKED

    def combo_down(self, t_ms: float) -> Action:
        if self._state == _State.IDLE:
            self._state = _State.PRESSED
            self._t0 = t_ms
            self._swallow_up = False
            return Action.START
        if self._state == _State.LOCKED:
            self._state = _State.IDLE
            self._swallow_up = True
            return Action.STOP
        return Action.NONE  # key autorepeat while held

    def combo_up(self, t_ms: float) -> Action:
        if self._swallow_up:
            self._swallow_up = False
            return Action.NONE
        if self._state == _State.PRESSED:
            if self.lock_enabled and (t_ms - self._t0) < self.tap_ms:
                self._state = _State.LOCKED
                return Action.NONE
            self._state = _State.IDLE
            return Action.STOP
        return Action.NONE

    def toggle_tap(self, t_ms: float) -> Action:
        """Toggle mode: one clean tap starts hands-free recording, the
        next one stops it. Used when the hotkey is e.g. a bare Left Alt."""
        if self._state == _State.IDLE:
            self._state = _State.LOCKED
            self._t0 = t_ms
            self._swallow_up = False
            return Action.START
        self._state = _State.IDLE
        self._swallow_up = False
        return Action.STOP

    def escape(self, t_ms: float) -> Action:
        if self._state == _State.PRESSED:
            self._state = _State.IDLE
            self._swallow_up = True  # combo is still physically held
            return Action.CANCEL
        if self._state == _State.LOCKED:
            self._state = _State.IDLE
            return Action.CANCEL
        return Action.NONE
