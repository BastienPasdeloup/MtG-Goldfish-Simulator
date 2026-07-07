"""Import a deck from a Moxfield URL.

Moxfield already classifies cards into boards (mainboard / commanders /
companions / sideboard), which we treat as the user's intent. We then
cross-validate against Scryfall's card facts so that mis-classified cards are
surfaced as warnings rather than silently accepted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx

from .models import CardData, Deck, DeckBoard, DeckEntry
from .scryfall import ScryfallClient

_MOXFIELD_API = "https://api2.moxfield.com/v3/decks/all/{public_id}"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_BOARD_MAP = {
    "mainboard": DeckBoard.MAINBOARD,
    "commanders": DeckBoard.COMMANDER,
    "companions": DeckBoard.COMPANION,
    "sideboard": DeckBoard.SIDEBOARD,
}


class MoxfieldError(RuntimeError):
    pass


@dataclass
class ImportResult:
    deck: Deck
    warnings: list[str] = field(default_factory=list)


def extract_public_id(url_or_id: str) -> str:
    """Pull the Moxfield public id out of a deck URL (or accept a bare id)."""
    url_or_id = url_or_id.strip()
    m = re.search(r"moxfield\.com/decks/([A-Za-z0-9_-]+)", url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{5,}", url_or_id):
        return url_or_id
    raise MoxfieldError(f"Could not find a Moxfield deck id in {url_or_id!r}")


def _fetch_moxfield_json(public_id: str) -> dict:
    url = _MOXFIELD_API.format(public_id=public_id)
    headers = {"User-Agent": _BROWSER_UA, "Accept": "application/json"}
    try:
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise MoxfieldError(f"Network error contacting Moxfield: {exc}") from exc
    if resp.status_code == 404:
        raise MoxfieldError(f"Moxfield deck {public_id!r} not found (is it public?)")
    if resp.status_code != 200:
        raise MoxfieldError(
            f"Moxfield returned HTTP {resp.status_code}. Public decks only; the "
            "API may also be rate-limiting or blocking automated access."
        )
    return resp.json()


def _iter_board_cards(boards: dict) -> list[tuple[DeckBoard, str, int]]:
    """Yield (board, card_name, quantity) across all known Moxfield boards."""
    out: list[tuple[DeckBoard, str, int]] = []
    for board_key, board in boards.items():
        target = _BOARD_MAP.get(board_key)
        if target is None:
            continue
        for entry in (board.get("cards") or {}).values():
            card = entry.get("card") or {}
            name = card.get("name")
            if not name:
                continue
            out.append((target, name, int(entry.get("quantity", 1))))
    return out


def import_moxfield_deck(
    url: str,
    name: str,
    format_id: str = "duel_commander",
    scryfall: ScryfallClient | None = None,
) -> ImportResult:
    """Import a public Moxfield deck and enrich it with Scryfall data."""
    scryfall = scryfall or ScryfallClient()
    public_id = extract_public_id(url)
    raw = _fetch_moxfield_json(public_id)

    boards = raw.get("boards") or {}
    if not boards:
        raise MoxfieldError("Moxfield response contained no boards.")

    board_cards = _iter_board_cards(boards)
    unique_names = sorted({n for _, n, _ in board_cards})
    card_index: dict[str, CardData] = scryfall.get_collection(unique_names)

    warnings: list[str] = []
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


def _validate_roles(deck: Deck, warnings: list[str]) -> None:
    """Cross-check Moxfield's commander/companion assignment against card facts."""
    for entry in deck.commanders:
        if not entry.card.can_be_commander:
            warnings.append(
                f"{entry.card.name!r} is marked as a commander but is not a "
                "legendary creature (nor grants commander status)."
            )
    for entry in deck.companions:
        if not entry.card.is_companion:
            warnings.append(
                f"{entry.card.name!r} is marked as a companion but has no "
                "companion ability."
            )
    if not deck.commanders:
        warnings.append("No commander detected in this deck.")
