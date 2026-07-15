"""Session store robustness: atomic saves and salvaging loads.

A session file must ALWAYS be loadable: interleaved/interrupted writes used to
leave trailing bytes after the JSON (and legacy run formats stopped
validating), which made sessions silently disappear from the picker.
"""
from __future__ import annotations

import pytest

from mtg_goldfish.deck.models import CardData, Deck, DeckBoard, DeckEntry
from mtg_goldfish.session.models import Session, SimConfig, SimResult
from mtg_goldfish.session.store import SessionCorrupt, SessionStore, new_id, now_iso


def _session(sid: str = "abc123def456") -> Session:
    deck = Deck(
        name="test",
        entries=[DeckEntry(
            board=DeckBoard.COMMANDER,
            card=CardData(name="Nick Fury, Agent of S.H.I.E.L.D.",
                          type_line="Legendary Creature — Human Spy Hero"),
        )],
    )
    return Session(id=sid, name="test", created_at=now_iso(), deck=deck)


def _result(status: str = "done", **extra) -> SimResult:
    return SimResult(id=new_id(), created_at=now_iso(), config=SimConfig(),
                     status=status, **extra)


@pytest.fixture
def store(tmp_path) -> SessionStore:
    return SessionStore(data_dir=tmp_path)


def test_save_load_roundtrip(store):
    s = _session()
    s.results.append(_result())
    store.save(s)
    loaded = store.load(s.id)
    assert loaded.name == "test" and len(loaded.results) == 1
    assert not list(store.dir.glob("*.tmp"))  # atomic save leaves no temp file


def test_load_salvages_trailing_garbage(store):
    """Interleaved concurrent writes: complete JSON + tail of an older dump."""
    s = _session()
    s.results.append(_result())
    store.save(s)
    path = store._path(s.id)
    path.write_text(path.read_text() + '"]}],"leftover":123}\n')
    loaded = store.load(s.id)
    assert loaded.id == s.id and len(loaded.results) == 1
    # the repaired file was written back: the fast path now succeeds
    Session.model_validate_json(path.read_text())


def test_load_salvages_legacy_results(store):
    """A run whose replay payload no longer validates keeps its stats."""
    s = _session()
    s.results.append(_result(stats={"successes": 3}))
    store.save(s)
    path = store._path(s.id)
    import json
    data = json.loads(path.read_text())
    # legacy format: sample_success_logs held strings, not frame dicts
    data["results"][0]["sample_success_logs"] = [["T1 play island", "T2 pass"]]
    data["results"].append("not-a-run-at-all")
    path.write_text(json.dumps(data))
    loaded = store.load(s.id)
    assert len(loaded.results) == 1  # bogus entry dropped, legacy run kept
    assert loaded.results[0].stats == {"successes": 3}
    assert loaded.results[0].sample_success_logs == []  # payload stripped


def test_load_unrecoverable_raises(store):
    s = _session()
    store.save(s)
    store._path(s.id).write_text('{"id": "abc123def456", "resu')  # truncated
    with pytest.raises(SessionCorrupt):
        store.load(s.id)


def test_list_sessions_includes_salvaged(store):
    s = _session()
    store.save(s)
    path = store._path(s.id)
    path.write_text(path.read_text() + "GARBAGE")
    listed = store.list_sessions()
    assert [m["id"] for m in listed] == [s.id]


def test_list_sessions_skips_unrecoverable(store):
    good, bad = _session("a" * 12), _session("b" * 12)
    store.save(good)
    store.save(bad)
    store._path(bad.id).write_text("not json at all")
    listed = store.list_sessions()
    assert [m["id"] for m in listed] == [good.id]
