from whispr.hotkey import Action, PTTStateMachine


def make(tap_ms=280, lock_enabled=True):
    return PTTStateMachine(tap_ms=tap_ms, lock_enabled=lock_enabled)


def test_press_starts_recording():
    sm = make()
    assert sm.combo_down(0) == Action.START
    assert sm.recording is True


def test_long_hold_release_stops():
    sm = make()
    sm.combo_down(0)
    assert sm.combo_up(1000) == Action.STOP
    assert sm.recording is False


def test_quick_tap_locks_hands_free():
    sm = make()
    sm.combo_down(0)
    assert sm.combo_up(100) == Action.NONE  # tap -> stay recording, locked
    assert sm.recording is True


def test_second_tap_stops_locked_recording():
    sm = make()
    sm.combo_down(0)
    sm.combo_up(100)  # locked
    assert sm.combo_down(2000) == Action.STOP
    assert sm.recording is False
    # release of that second tap is swallowed
    assert sm.combo_up(2100) == Action.NONE


def test_quick_tap_stops_when_lock_disabled():
    sm = make(lock_enabled=False)
    sm.combo_down(0)
    assert sm.combo_up(100) == Action.STOP
    assert sm.recording is False


def test_autorepeat_down_events_ignored_while_held():
    sm = make()
    assert sm.combo_down(0) == Action.START
    assert sm.combo_down(50) == Action.NONE  # key autorepeat
    assert sm.combo_down(100) == Action.NONE
    assert sm.combo_up(1000) == Action.STOP


def test_escape_cancels_while_holding():
    sm = make()
    sm.combo_down(0)
    assert sm.escape(500) == Action.CANCEL
    assert sm.recording is False
    # subsequent release does nothing
    assert sm.combo_up(600) == Action.NONE


def test_escape_cancels_locked_recording():
    sm = make()
    sm.combo_down(0)
    sm.combo_up(100)  # locked
    assert sm.escape(2000) == Action.CANCEL
    assert sm.recording is False


def test_escape_ignored_when_idle():
    sm = make()
    assert sm.escape(0) == Action.NONE


def test_locked_property_reflects_hands_free_state():
    sm = make()
    assert sm.locked is False
    sm.combo_down(0)
    assert sm.locked is False  # push-to-talk hold, not locked
    sm.combo_up(100)  # quick tap -> hands-free lock
    assert sm.locked is True
    sm.combo_down(2000)  # tap again -> stop
    assert sm.locked is False


def test_full_cycle_can_repeat():
    sm = make()
    sm.combo_down(0)
    sm.combo_up(1000)  # stop
    assert sm.combo_down(2000) == Action.START
    assert sm.combo_up(3000) == Action.STOP
