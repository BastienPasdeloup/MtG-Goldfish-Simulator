"""URL-dispatching deck import: pick the right source (Moxfield / MTGTop8)."""
from __future__ import annotations

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
    """Import a deck from a Moxfield or mtgtop8 URL, chosen by the URL host.
    When `format_id` is None the format is inferred from the source deck."""
    if _is_mtgtop8(url):
        return import_mtgtop8_deck(url, name, format_id, scryfall)
    return import_moxfield_deck(url, name, format_id, scryfall)


def fetch_deck_signature(url: str, format_id: str | None = None) -> list:
    """Current content signature of the source deck (for change detection)."""
    if _is_mtgtop8(url):
        return _t8_sig(url, format_id)
    return _mox_sig(url)


__all__ = ["import_deck", "fetch_deck_signature", "deck_signature", "Deck"]
