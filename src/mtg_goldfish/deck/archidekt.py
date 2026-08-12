"""Import a deck from an Archidekt URL.

Archidekt's public API (`/api/decks/<id>/`) returns every card with a `quantity`
and a list of `categories` (names). A handful of category names are meaningful as
BOARDS — "Commander", "Companion", "Sideboard", "Maybeboard" — and any deck-level
category flagged `includedInDeck: false` is a "considering" pile that isn't part of
the deck. Everything else is the mainboard.
"""
from __future__ import annotations

import re

import httpx

from .models import CardData, Deck, DeckBoard, DeckEntry
from .moxfield import ImportResult  # shared {deck, warnings} result shape
from .scryfall import ScryfallClient, ScryfallError

_ARCHIDEKT_API = "https://archidekt.com/api/decks/{deck_id}/"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


#: Archidekt's `deckFormat` is a numeric id. Map the common ones to our format
#: ids (commander variants → Duel Commander; the rest → constructed formats).
_ARCHIDEKT_FORMAT = {
    1: "standard", 2: "modern", 3: "duel_commander", 4: "legacy", 5: "vintage",
    6: "pauper", 10: "penny", 11: "duel_commander", 12: "duel_commander",
    13: "duel_commander", 14: "duel_commander", 15: "pioneer", 16: "historic",
    17: "duel_commander", 18: "alchemy", 19: "explorer", 20: "duel_commander",
    22: "premodern",
}


class ArchidektError(RuntimeError):
    pass


def is_archidekt(url: str) -> bool:
    return "archidekt.com" in (url or "").lower()


def extract_deck_id(url_or_id: str) -> str:
    """Pull the numeric Archidekt deck id out of a URL (or accept a bare id)."""
    url_or_id = (url_or_id or "").strip()
    m = re.search(r"archidekt\.com/(?:decks|api/decks)/(\d+)", url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{2,}", url_or_id):
        return url_or_id
    raise ArchidektError(f"Could not find an Archidekt deck id in {url_or_id!r}")


def _fetch_archidekt_json(deck_id: str) -> dict:
    url = _ARCHIDEKT_API.format(deck_id=deck_id)
    headers = {"User-Agent": _BROWSER_UA, "Accept": "application/json"}
    try:
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise ArchidektError(f"Network error contacting Archidekt: {exc}") from exc
    if resp.status_code == 404:
        raise ArchidektError(f"Archidekt deck {deck_id!r} not found (is it public?)")
    if resp.status_code != 200:
        raise ArchidektError(
            f"Archidekt returned HTTP {resp.status_code}. Public decks only; the "
            "API may also be rate-limiting or blocking automated access."
        )
    return resp.json()


def _card_name(entry: dict) -> str | None:
    card = entry.get("card") or {}
    oracle = card.get("oracleCard") or {}
    return oracle.get("name") or card.get("name")


def _board_for(cats: list[str], excluded: set[str]) -> DeckBoard | None:
    """Map a card's Archidekt categories to a board (None = not in the deck)."""
    low = {c.lower() for c in cats}
    if "maybeboard" in low:
        return None
    if "commander" in low:
        return DeckBoard.COMMANDER
    if "companion" in low:
        return DeckBoard.COMPANION
    if "sideboard" in low:
        return DeckBoard.SIDEBOARD
    # A card whose ONLY categories are "not included in the deck" custom piles is
    # a considering/reference card — skip it.
    if cats and all(c in excluded for c in cats):
        return None
    return DeckBoard.MAINBOARD


def _iter_board_cards(raw: dict) -> list[tuple[DeckBoard, str, int]]:
    excluded = {
        c.get("name") for c in (raw.get("categories") or [])
        if not c.get("includedInDeck", True)
        and (c.get("name") or "").lower() not in ("sideboard", "commander", "companion")
    }
    out: list[tuple[DeckBoard, str, int]] = []
    for entry in raw.get("cards") or []:
        name = _card_name(entry)
        if not name:
            continue
        board = _board_for(entry.get("categories") or [], excluded)
        if board is None:
            continue
        out.append((board, name, int(entry.get("quantity", 1) or 1)))
    return out


def fetch_deck_signature(url: str, scryfall: ScryfallClient | None = None
                         ) -> list[tuple[str, str, int]]:
    """The deck's CURRENT content signature (matches `deck_signature`'s shape).

    Names are resolved through Scryfall to their canonical `front // back` form —
    exactly as `import_archidekt_deck` does — so a just-imported deck doesn't look
    "changed" only because Archidekt prints a DFC front-face-only or spells a name
    differently (accents, punctuation)."""
    scryfall = scryfall or ScryfallClient()
    raw = _fetch_archidekt_json(extract_deck_id(url))
    board_cards = _iter_board_cards(raw)
    index = scryfall.get_collection(sorted({n for _, n, _ in board_cards}))
    rows: list[tuple[str, str, int]] = []
    for board, name, qty in board_cards:
        card = index.get(name)
        if card is None:
            try:
                card = scryfall.get_named(name)
            except ScryfallError:
                card = None
        rows.append((board.value, card.name if card else name, qty))
    return sorted(rows)


def import_archidekt_deck(
    url: str,
    name: str,
    format_id: str | None = None,
    scryfall: ScryfallClient | None = None,
) -> ImportResult:
    """Import a public Archidekt deck and enrich it with Scryfall data."""
    from ..formats import resolve_format_id  # deferred: avoids an import cycle
    from .moxfield import _validate_roles

    scryfall = scryfall or ScryfallClient()
    raw = _fetch_archidekt_json(extract_deck_id(url))
    # Archidekt's `deckFormat` is a numeric id — map it directly; fall back to
    # resolve_format_id (defaults to Duel Commander) for anything unrecognised.
    fmt = raw.get("deckFormat")
    format_id = format_id or _ARCHIDEKT_FORMAT.get(fmt) or resolve_format_id(None)

    board_cards = _iter_board_cards(raw)
    if not board_cards:
        raise ArchidektError("Archidekt deck contained no cards.")
    unique_names = sorted({n for _, n, _ in board_cards})
    card_index: dict[str, CardData] = scryfall.get_collection(unique_names)

    warnings: list[str] = []
    for card_name in unique_names:
        if card_name not in card_index:
            try:
                card_index[card_name] = scryfall.get_named(card_name)
            except ScryfallError:
                pass

    entries: list[DeckEntry] = []
    for board, card_name, qty in board_cards:
        card = card_index.get(card_name)
        if card is None:
            warnings.append(f"Could not resolve {card_name!r} on Scryfall; skipped.")
            continue
        entries.append(DeckEntry(quantity=qty, board=board, card=card))

    deck = Deck(
        name=name or raw.get("name", "Untitled deck"),
        format_id=format_id,
        source_url=url,
        entries=entries,
    )
    _validate_roles(deck, warnings)
    return ImportResult(deck=deck, warnings=warnings)
