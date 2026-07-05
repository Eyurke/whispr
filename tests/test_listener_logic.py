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
