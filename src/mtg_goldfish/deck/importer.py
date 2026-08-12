"""URL-dispatching deck import: pick the right source (Moxfield / MTGTop8 /
Archidekt)."""
from __future__ import annotations

from .archidekt import (fetch_deck_signature as _arch_sig, import_archidekt_deck,
                        is_archidekt)
from .models import Deck
from .moxfield import (ImportResult, deck_signature, fetch_deck_signature as _mox_sig,
                       import_moxfield_deck)
from .mtgtop8 import (fetch_deck_signature as _t8_sig, import_mtgtop8_deck)
from .scryfall import ScryfallClient


def _is_mtgtop8(url: str) -> bool:
    return "mtgtop8.com" in (url or "").lower()


def import_deck(
    url: str,
    name: str,
    format_id: str | None = None,
    scryfall: ScryfallClient | None = None,
) -> ImportResult:
    """Import a deck from a Moxfield, mtgtop8, or Archidekt URL, chosen by the URL
    host. When `format_id` is None the format is inferred from the source deck."""
    if _is_mtgtop8(url):
        result = import_mtgtop8_deck(url, name, format_id, scryfall)
    elif is_archidekt(url):
        result = import_archidekt_deck(url, name, format_id, scryfall)
    else:
        result = import_moxfield_deck(url, name, format_id, scryfall)
    # Record each card's ORIGINAL board so later maindeck↔sideboard drags can be
    # badged (MD/SB) against the import.
    for entry in result.deck.entries:
        if entry.orig_board is None:
            entry.orig_board = entry.board
    return result


def fetch_deck_signature(url: str, format_id: str | None = None) -> list:
    """Current content signature of the source deck (for change detection)."""
    if _is_mtgtop8(url):
        return _t8_sig(url, format_id)
    if is_archidekt(url):
        return _arch_sig(url)
    return _mox_sig(url)


__all__ = ["import_deck", "fetch_deck_signature", "deck_signature", "Deck"]
