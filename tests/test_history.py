import pytest

from whispr.history import History


@pytest.fixture
def hist(tmp_path):
    h = History(tmp_path / "history.db")
    yield h
    h.close()


def test_add_and_recent(hist):
    hist.add("hello world out there", 2.0)
    entries = hist.recent()
    assert len(entries) == 1
    assert entries[0].text == "hello world out there"
    assert entries[0].words == 4
    assert entries[0].duration_s == 2.0


def test_recent_returns_newest_first(hist):
    hist.add("first", 1.0)
    hist.add("second", 1.0)
    entries = hist.recent()
    assert [e.text for e in entries] == ["second", "first"]


def test_search_filters_text(hist):
    hist.add("the quick brown fox", 1.0)
    hist.add("an unrelated note", 1.0)
    entries = hist.recent(search="fox")
    assert len(entries) == 1
    assert "fox" in entries[0].text


def test_delete_removes_entry(hist):
    eid = hist.add("delete me", 1.0)
    hist.delete(eid)
    assert hist.recent() == []


def test_clear_removes_everything(hist):
    hist.add("one", 1.0)
    hist.add("two", 1.0)
    hist.clear()
    assert hist.recent() == []


def test_stats_aggregates_words_and_wpm(hist):
    hist.add("one two three four five six", 3.0)  # 6 words in 3s -> 120 wpm
    s = hist.stats()
    assert s["entries"] == 1
    assert s["words"] == 6
    assert round(s["avg_wpm"]) == 120


def test_persists_across_reopen(tmp_path):
    db = tmp_path / "history.db"
    h1 = History(db)
    h1.add("persisted", 1.0)
    h1.close()

    h2 = History(db)
    try:
        assert h2.recent()[0].text == "persisted"
    finally:
        h2.close()
