"""Unit tests for the MTGTop8 decklist parser (no network)."""
import pytest

from mtg_goldfish.deck import mtgtop8
from mtg_goldfish.deck.mtgtop8 import (MTGTop8Error, _normalize_name,
                                       _parse_decklist, extract_deck_id,
                                       resolve_deck_id)

_SAMPLE = """1 Mountain
1 Swamp
1 Spiked Corridor/Torture Pit
1 Sundering Eruption
Sideboard
1 Ellie, Vengeful Hunter
1 Ellie, Brick Master"""


def test_extract_deck_id():
    assert extract_deck_id("https://www.mtgtop8.com/event?e=87792&d=866126&f=EDH") == "866126"
    assert extract_deck_id("https://www.mtgtop8.com/deck?d=42") == "42"
    assert extract_deck_id("866126") == "866126"
    with pytest.raises(MTGTop8Error):
        extract_deck_id("https://www.moxfield.com/decks/abc")


# An abridged event page: the 64 sibling decks appear only as listing anchors
# (?e=..&d=..), while the DISPLAYED deck also shows up in the single-deck script
# URLs (mtgarena / mtgo / price_tcg). Only the latter is what we want.
_EVENT_HTML = """
<a href="event?e=87792&d=866126&f=EDH">Other deck</a>
<a href="event?e=87792&d=866127&f=EDH">Another deck</a>
RequestContent("price_tcg?f=EDH&d=866125", "tcg_price");
src=mtgarena?d=866125>
<a onclick="LoadExpl('e=87792&d=866125&f=EDH&exp_lang=EN');">export</a>
"""


def test_resolve_deck_id_direct_deck_url_needs_no_network(monkeypatch):
    # A URL that already carries d= must NOT hit the network.
    monkeypatch.setattr(mtgtop8, "_http_get",
                        lambda *_: pytest.fail("should not fetch for a d= URL"))
    assert resolve_deck_id("https://www.mtgtop8.com/event?e=87792&d=866126&f=EDH") == "866126"
    assert resolve_deck_id("866125") == "866125"


def test_resolve_deck_id_event_url_scrapes_displayed_deck(monkeypatch):
    class _Resp:
        status_code = 200
        text = _EVENT_HTML

    monkeypatch.setattr(mtgtop8, "_http_get", lambda url: _Resp())
    # No d= but an e= event id → resolves to the displayed (winning) deck.
    assert resolve_deck_id("https://www.mtgtop8.com/event?e=87792&f=EDH") == "866125"


def test_resolve_deck_id_event_url_without_a_deck_errors(monkeypatch):
    class _Resp:
        status_code = 200
        text = "<html>no decks here</html>"

    monkeypatch.setattr(mtgtop8, "_http_get", lambda url: _Resp())
    with pytest.raises(MTGTop8Error):
        resolve_deck_id("https://www.mtgtop8.com/event?e=99999&f=EDH")


def test_normalize_name():
    assert _normalize_name("[LRW] Thoughtseize") == "Thoughtseize"
    assert _normalize_name("Spiked Corridor/Torture Pit") == "Spiked Corridor // Torture Pit"
    assert _normalize_name("Claim/Fame") == "Claim // Fame"
    assert _normalize_name("Sundering Eruption") == "Sundering Eruption"
    # Already-canonical // is left alone.
    assert _normalize_name("Boggart Trawler // Boggart Bog") == "Boggart Trawler // Boggart Bog"


def test_parse_decklist_splits_commander_into_sideboard():
    main, side = _parse_decklist(_SAMPLE)
    assert (1, "Mountain") in main and (1, "Swamp") in main
    assert (1, "Spiked Corridor // Torture Pit") in main
    assert len(main) == 4
    assert side == [(1, "Ellie, Vengeful Hunter"), (1, "Ellie, Brick Master")]


def test_parse_decklist_handles_explicit_sb_prefix():
    main, side = _parse_decklist("1 Mountain\nSB: 1 Ellie, Brick Master")
    assert main == [(1, "Mountain")]
    assert side == [(1, "Ellie, Brick Master")]
