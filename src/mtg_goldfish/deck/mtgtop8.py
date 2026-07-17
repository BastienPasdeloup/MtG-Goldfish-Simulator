"""Import a deck from an mtgtop8.com deck/event URL.

MTGTop8 exposes a plain-text MTGO decklist at ``/mtgo?d=<deck id>``: one
``<qty> <card name>`` line per card, then a ``Sideboard`` marker followed by any
sideboard cards. For Commander/EDH events MTGTop8 stores the commander(s) in that
sideboard slot, so for a commander format we treat the post-``Sideboard`` cards
as the commander(s). Card facts are enriched from Scryfall (which also resolves
the split ``A/B`` and front-only modal-DFC names MTGTop8 prints).

A URL may point at a specific deck (``?d=<id>``) or at an event
(``event?e=<id>&f=EDH`` with no ``d=``). An event URL shows the event's default
(winning) deck; we resolve that deck's id by scraping the event page."""
from __future__ import annotations

import re

import httpx

from .models import CardData, Deck, DeckBoard, DeckEntry
from .moxfield import ImportResult, _validate_roles
from .scryfall import ScryfallClient, ScryfallError

_MTGO_EXPORT = "https://www.mtgtop8.com/mtgo?d={deck_id}"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_LINE_RE = re.compile(r"^(?:SB:\s*)?(\d+)\s+(.+)$")
_COMMANDER_FORMATS = {"duel_commander", "commander", "edh"}
#: On an event page the currently-displayed deck's id appears in a handful of
#: single-deck script URLs (the Arena/MTGO export links and the price widget),
#: unlike the sibling-deck ids which only occur in listing anchors.
_DISPLAYED_DECK_RE = re.compile(r"(?:mtgarena|mtgo|price_tcg)\?[^\"']*?\bd=(\d+)")


class MTGTop8Error(RuntimeError):
    pass


def _http_get(url: str) -> httpx.Response:
    headers = {"User-Agent": _BROWSER_UA, "Accept": "text/html,text/plain"}
    try:
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
            return client.get(url)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise MTGTop8Error(f"Network error contacting mtgtop8: {exc}") from exc


def extract_deck_id(url_or_id: str) -> str:
    """Pull the numeric deck id out of an mtgtop8 URL (``?d=...``/``&d=...``) or
    accept a bare id. Does NOT hit the network — use `resolve_deck_id` for event
    URLs that carry only ``e=``."""
    s = url_or_id.strip()
    m = re.search(r"[?&]d=(\d+)", s)
    if m:
        return m.group(1)
    if s.isdigit():
        return s
    raise MTGTop8Error(f"Could not find an mtgtop8 deck id in {url_or_id!r}")


def _resolve_event_deck_id(event_url: str) -> str:
    """Scrape an event page (``event?e=<id>`` with no ``d=``) for the deck it
    displays by default — the event winner."""
    resp = _http_get(event_url)
    if resp.status_code != 200 or not resp.text.strip():
        raise MTGTop8Error(
            f"mtgtop8 returned HTTP {resp.status_code} for {event_url!r} "
            "(is the event link correct?)")
    m = _DISPLAYED_DECK_RE.search(resp.text)
    if not m:
        raise MTGTop8Error(
            f"Could not find a deck on the mtgtop8 event page {event_url!r}. "
            "Open a specific deck and paste its URL (it will contain 'd=').")
    return m.group(1)


def resolve_deck_id(url_or_id: str) -> str:
    """Deck id for any mtgtop8 URL. A deck URL carries ``d=`` directly (no
    network); an event URL (``event?e=...`` with no ``d=``) is scraped for its
    default deck."""
    s = (url_or_id or "").strip()
    if not re.search(r"[?&]d=\d+", s) and re.search(r"[?&]e=\d+", s):
        return _resolve_event_deck_id(s)
    return extract_deck_id(s)


def _normalize_name(raw: str) -> str:
    """Clean a MTGTop8 card name: strip a leading ``[SET]`` code and rewrite a
    split/DFC ``A/B`` into Scryfall's ``A // B`` form."""
    name = re.sub(r"^\[[^\]]*\]\s*", "", raw).strip()
    if "/" in name and "//" not in name:
        name = " // ".join(part.strip() for part in name.split("/"))
    return name


def _parse_decklist(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Return (mainboard, sideboard) as lists of (quantity, card name)."""
    main: list[tuple[int, str]] = []
    side: list[tuple[int, str]] = []
    in_side = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.lower() in ("sideboard", "sb:"):
            in_side = True
            continue
        explicit_sb = line.upper().startswith("SB:")
        m = _LINE_RE.match(line)
        if not m:
            continue
        entry = (int(m.group(1)), _normalize_name(m.group(2)))
        (side if in_side or explicit_sb else main).append(entry)
    return main, side


def _fetch_mtgtop8_decklist(deck_id: str) -> str:
    resp = _http_get(_MTGO_EXPORT.format(deck_id=deck_id))
    if resp.status_code != 200 or not resp.text.strip():
        raise MTGTop8Error(
            f"mtgtop8 returned HTTP {resp.status_code} for deck {deck_id!r} "
            "(is the deck id correct?)")
    return resp.text


def _resolve_names(scryfall: ScryfallClient, names: list[str]) -> tuple[dict, list[str]]:
    unique = sorted(set(names))
    index: dict[str, CardData] = scryfall.get_collection(unique)
    warnings: list[str] = []
    for name in unique:
        if name not in index:
            try:  # split / DFC names the bulk endpoint misses
                index[name] = scryfall.get_named(name)
            except ScryfallError:
                pass
    return index, warnings


def import_mtgtop8_deck(
    url: str,
    name: str,
    format_id: str | None = None,
    scryfall: ScryfallClient | None = None,
) -> ImportResult:
    """Import a public mtgtop8 deck and enrich it with Scryfall data. The MTGO
    text export carries no format, so we default to Duel Commander (the only
    modelled format) unless an explicit `format_id` is given."""
    format_id = format_id or "duel_commander"
    scryfall = scryfall or ScryfallClient()
    deck_id = resolve_deck_id(url)
    text = _fetch_mtgtop8_decklist(deck_id)
    main, side = _parse_decklist(text)
    if not main and not side:
        raise MTGTop8Error("mtgtop8 export contained no cards.")

    index, warnings = _resolve_names(scryfall, [n for _, n in main + side])
    # In a commander format the "sideboard" holds the commander(s).
    side_board = (DeckBoard.COMMANDER if format_id in _COMMANDER_FORMATS
                  else DeckBoard.SIDEBOARD)

    entries: list[DeckEntry] = []
    for board, rows in ((DeckBoard.MAINBOARD, main), (side_board, side)):
        for qty, card_name in rows:
            card = index.get(card_name)
            if card is None:
                warnings.append(f"Could not resolve {card_name!r} on Scryfall; skipped.")
                continue
            entries.append(DeckEntry(quantity=qty, board=board, card=card))

    deck = Deck(
        name=name or f"MTGTop8 deck {deck_id}",
        format_id=format_id,
        source_url=url,
        entries=entries,
    )
    _validate_roles(deck, warnings)
    return ImportResult(deck=deck, warnings=warnings)


def fetch_deck_signature(url: str, format_id: str | None = None,
                         scryfall: ScryfallClient | None = None) -> list[tuple[str, str, int]]:
    """Current content signature of the mtgtop8 deck (matches
    moxfield.deck_signature's shape) for change detection.

    Names are resolved through Scryfall to their canonical ``front // back``
    form — exactly as `import_mtgtop8_deck` does — because the stored deck's
    `CardData.name` is already canonical. mtgtop8 prints modal/transform DFCs
    front-face only, so without this the signature would never match and the
    deck would always look 'changed'."""
    scryfall = scryfall or ScryfallClient()
    format_id = format_id or "duel_commander"
    text = _fetch_mtgtop8_decklist(resolve_deck_id(url))
    main, side = _parse_decklist(text)
    index, _ = _resolve_names(scryfall, [n for _, n in main + side])
    side_board = (DeckBoard.COMMANDER if format_id in _COMMANDER_FORMATS
                  else DeckBoard.SIDEBOARD)
    rows: list[tuple[str, str, int]] = []
    for board, entries in ((DeckBoard.MAINBOARD, main), (side_board, side)):
        for qty, name in entries:
            card = index.get(name)
            if card is not None:  # skip unresolved names, mirroring import
                rows.append((board.value, card.name, qty))
    return sorted(rows)
