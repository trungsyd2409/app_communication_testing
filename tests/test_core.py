"""Tests for storage, picker and the Google Drive link parser (no GUI needed).

Run:  python -m pytest tests
"""
import random
from collections import Counter

import pytest

from speakdaily import drive_sync, picker
from speakdaily.storage import Question, Store, parse_csv_text


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def test_starter_questions_load(store):
    assert len(store.questions) >= 40
    assert all(q.source == "starter" for q in store.questions)
    assert all(q.reference_answer for q in store.questions)
    assert len(store.topics()) >= 10


def test_random_time_always_between_1_and_10(store):
    rng = random.Random(1)
    for q in store.questions:
        for mode in ("random", "quick"):
            for _ in range(50):
                m = picker.random_minutes(q, mode, rng)
                assert 1 <= m <= 10
                assert (m * 2) == int(m * 2)          # half-minute steps
                if mode == "quick":
                    assert m <= 3


def test_random_time_uses_full_range():
    q = Question(id="x", topic="t", question="?", min_minutes=1, max_minutes=10)
    rng = random.Random(3)
    values = {picker.random_minutes(q, "random", rng) for _ in range(2000)}
    assert min(values) == 1 and max(values) == 10


def test_shuffle_bag_no_repeats(store):
    rng = random.Random(7)
    n = len(store.questions)
    seen = [picker.next_question(store, rng=rng).id for _ in range(n)]
    assert len(set(seen)) == n                    # every question once per round
    again = picker.next_question(store, rng=rng)  # new round starts
    assert again is not None


def test_topic_filter(store):
    topic = store.topics()[0]
    for _ in range(10):
        assert picker.next_question(store, [topic]).topic == topic


def test_low_rating_comes_up_more(store):
    hard = store.questions[0]
    store.history.append({"question_id": hard.id, "rating": 1,
                          "finished_at": "2026-11-01T10:00:00", "spoken_seconds": 60})
    rng = random.Random(5)
    firsts = Counter()
    for _ in range(400):
        store.settings["bag"] = []
        firsts[picker.next_question(store, rng=rng).id] += 1
    assert firsts[hard.id] > 400 / len(store.questions) * 1.5


CSV = """Topic,Question,Answer,Key Phrases,Level,Min,Max
Work,What do you do?,I am a data analyst.,data analyst; I work on,easy,2,4
Travel,Best trip?,Da Lat.,would love to,,,
,,,,,,
Food,Favourite food?,Pho,,hard,12,0
"""


def test_parse_sheet_csv_with_header_aliases():
    qs = parse_csv_text(CSV, source="drive")
    assert [q.topic for q in qs] == ["Work", "Travel", "Food"]
    assert qs[0].key_phrases == ["data analyst", "I work on"]
    assert (qs[0].min_minutes, qs[0].max_minutes) == (2, 4)
    assert (qs[1].min_minutes, qs[1].max_minutes) == (1, 10)
    assert (qs[2].min_minutes, qs[2].max_minutes) == (1, 10)   # clamped + swapped
    assert qs[2].difficulty == "hard"


def test_parse_needs_question_column():
    with pytest.raises(ValueError):
        parse_csv_text("topic,answer\na,b\n", "drive")


def test_drive_replace_keeps_local(store):
    local = Question(id=store.new_id(), topic="Mine", question="My own question?")
    store.upsert(local)
    store.replace_drive_questions(parse_csv_text(CSV, "drive"))
    sources = Counter(q.source for q in store.questions)
    assert sources == {"drive": 3, "local": 1}
    reloaded = Store(store.folder)
    assert len(reloaded.questions) == 4


def test_csv_roundtrip(store, tmp_path):
    out = tmp_path / "out.csv"
    n = store.export_csv(out)
    back = parse_csv_text(out.read_text(encoding="utf-8-sig"), "local")
    assert len(back) == n
    assert back[0].reference_answer == store.questions[0].reference_answer


@pytest.mark.parametrize("link,file_id,gid,is_sheet", [
    ("https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz123/edit#gid=42",
     "1AbCdEfGhIjKlMnOpQrStUvWxYz123", "42", True),
    ("https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz123/edit?usp=sharing",
     "1AbCdEfGhIjKlMnOpQrStUvWxYz123", None, True),
    ("https://drive.google.com/file/d/1ZZZZZZZZZZZZZZZZZZZZZZZZ/view?usp=drive_link",
     "1ZZZZZZZZZZZZZZZZZZZZZZZZ", None, False),
    ("1AbCdEfGhIjKlMnOpQrStUvWxYz123", "1AbCdEfGhIjKlMnOpQrStUvWxYz123", None, True),
])
def test_parse_link(link, file_id, gid, is_sheet):
    ref = drive_sync.parse_link(link)
    assert (ref.file_id, ref.gid, ref.is_sheet) == (file_id, gid, is_sheet)


def test_parse_link_errors():
    with pytest.raises(drive_sync.SyncError):
        drive_sync.parse_link("")
    with pytest.raises(drive_sync.SyncError):
        drive_sync.parse_link("https://example.com/whatever")


def test_stats_streak(store):
    for day in ("2026-11-07", "2026-11-08", "2026-11-09"):
        store.history.append({"finished_at": f"{day}T09:00:00", "spoken_seconds": 120,
                              "rating": 4})
    from datetime import date
    s = store.stats(date(2026, 11, 9))
    assert s["streak"] == 3 and s["today_minutes"] == 2 and s["avg_rating"] == 4


class FakeResponse:
    def __init__(self, status, text, ctype):
        self.status_code, self.text, self.headers, self.encoding = status, text, {"Content-Type": ctype}, None


def test_fetch_link_mode(monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return FakeResponse(200, CSV, "text/csv")
    monkeypatch.setattr(drive_sync.requests, "get", fake_get)
    qs = drive_sync.fetch_questions(
        "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz123/edit#gid=7")
    assert len(qs) == 3 and all(q.source == "drive" for q in qs)
    assert calls[0].endswith("/export?format=csv&gid=7")


def test_fetch_private_sheet_gives_share_hint(monkeypatch):
    monkeypatch.setattr(drive_sync.requests, "get",
                        lambda url, **kw: FakeResponse(200, "<html>Sign in</html>", "text/html; charset=utf-8"))
    with pytest.raises(drive_sync.SyncError, match="Anyone with the link"):
        drive_sync.fetch_questions("1AbCdEfGhIjKlMnOpQrStUvWxYz123")


def test_bundled_default_sheet(store):
    assert "docs.google.com" in store.settings["sheet_url"]
    assert drive_sync.parse_link(store.settings["sheet_url"]).gid == "1838261859"
