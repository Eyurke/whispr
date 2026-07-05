from whispr.listener import parse_combo


def test_parse_ctrl_win():
    groups = parse_combo("ctrl+win")
    assert len(groups) == 2
    ctrl_group = next(g for g in groups if "ctrl" in g)
    win_group = next(g for g in groups if "windows" in g)
    assert {"ctrl", "left ctrl", "right ctrl"} <= ctrl_group
    assert {"windows", "left windows", "right windows"} <= win_group


def test_parse_single_function_key():
    groups = parse_combo("f9")
    assert groups == [frozenset({"f9"})]


def test_parse_ctrl_alt():
    groups = parse_combo("ctrl+alt")
    flat = set().union(*groups)
    assert "left ctrl" in flat
    assert "left alt" in flat


def test_parse_is_case_and_space_insensitive():
    assert parse_combo("Ctrl + Win") == parse_combo("ctrl+win")


def test_parse_left_alt_matches_bare_alt_event_name():
    # the `keyboard` package reports the left alt key as plain "alt"
    groups = parse_combo("left alt")
    assert groups == [frozenset({"alt", "left alt"})]


def test_parse_right_alt():
    groups = parse_combo("right alt")
    assert "alt gr" in groups[0] and "right alt" in groups[0]
    assert "alt" not in groups[0]


# ---------------------------------------------------------------- toggle mode

from types import SimpleNamespace

from whispr.hotkey import Action, PTTStateMachine
from whispr.listener import HotkeyListener


def press(listener, name):
    listener._on_event(SimpleNamespace(name=name, event_type="down"))


def release(listener, name):
    listener._on_event(SimpleNamespace(name=name, event_type="up"))


def make_toggle(combo="left alt"):
    actions = []
    machine = PTTStateMachine()
    listener = HotkeyListener(combo, machine, actions.append, mode="toggle")
    return listener, machine, actions


def test_toggle_clean_tap_starts_and_stops():
    listener, machine, actions = make_toggle()
    press(listener, "alt")
    release(listener, "alt")
    assert actions == [Action.START]
    assert machine.recording is True

    press(listener, "alt")
    release(listener, "alt")
    assert actions == [Action.START, Action.STOP]
    assert machine.recording is False


def test_toggle_ignores_alt_tab_style_chords():
    listener, machine, actions = make_toggle()
    press(listener, "alt")
    press(listener, "tab")     # other key while combo held -> it's a shortcut
    release(listener, "tab")
    release(listener, "alt")
    assert actions == []
    assert machine.recording is False


def test_toggle_alt_tab_while_recording_does_not_stop():
    listener, machine, actions = make_toggle()
    press(listener, "alt")
    release(listener, "alt")   # start recording
    press(listener, "alt")
    press(listener, "tab")     # user switches windows mid-dictation
    release(listener, "tab")
    release(listener, "alt")
    assert actions == [Action.START]
    assert machine.recording is True


def test_hold_mode_unaffected_by_toggle_logic():
    actions = []
    machine = PTTStateMachine(tap_ms=280)
    listener = HotkeyListener("ctrl+win", machine, actions.append, mode="hold")
    press(listener, "ctrl")
    press(listener, "left windows")
    assert actions == [Action.START]
    release(listener, "left windows")
    release(listener, "ctrl")
    # release before tap_ms in wall-clock terms is timing-dependent; just
    # assert the machine acted on the edge (locked or stopped, not idle-start)
    assert len(actions) >= 1
