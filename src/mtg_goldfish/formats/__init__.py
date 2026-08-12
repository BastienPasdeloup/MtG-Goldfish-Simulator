"""Format registry."""
from __future__ import annotations

import re

from .base import Format
from .duel_commander import DUEL_COMMANDER


def _constructed(fid: str, name: str) -> Format:
    """A generic non-Commander 60-card constructed format (Legacy, Modern, …).
    Opponent-facing rules aren't modelled; what matters here is that there is NO
    commander (so a deck's post-`Sideboard` cards stay in the sideboard, not the
    command zone) and there's a real sideboard."""
    return Format(id=fid, name=name, starting_life=20, starting_hand_size=7,
                  deck_size=60, singleton=False, uses_commander=False,
                  uses_companion=True)


#: Non-Commander constructed formats. They share game-setup rules; only the label
#: differs. `constructed` is the generic fallback for an unrecognised 60-card deck.
_CONSTRUCTED = {
    "legacy": "Legacy", "modern": "Modern", "vintage": "Vintage",
    "standard": "Standard", "pioneer": "Pioneer", "pauper": "Pauper",
    "premodern": "Premodern", "historic": "Historic", "explorer": "Explorer",
    "alchemy": "Alchemy", "penny": "Penny Dreadful", "constructed": "Constructed",
}

_FORMATS: dict[str, Format] = {DUEL_COMMANDER.id: DUEL_COMMANDER}
for _fid, _name in _CONSTRUCTED.items():
    _FORMATS[_fid] = _constructed(_fid, _name)

#: Aliases mapping a deck source's declared format (normalized to lowercase
#: alphanumerics) onto a registered format id. Commander variants map to Duel
#: Commander (the only fully-modelled commander format); constructed variants map
#: to their generic constructed format.
_FORMAT_ALIASES = {
    "duelcommander": DUEL_COMMANDER.id,
    "commander": DUEL_COMMANDER.id,
    "commander1v1": DUEL_COMMANDER.id,
    "1v1commander": DUEL_COMMANDER.id,
    "frenchcommander": DUEL_COMMANDER.id,
    "cedh": DUEL_COMMANDER.id,
    "edh": DUEL_COMMANDER.id,
    "oldschool": "premodern",
    "oldschool93": "premodern",
    "pauperedh": DUEL_COMMANDER.id,
    "highlander": "legacy",
    "canadianhighlander": "legacy",
    "block": "standard",
    "extended": "modern",
    "brawl": DUEL_COMMANDER.id,
    "historicbrawl": DUEL_COMMANDER.id,
}


def get_format(format_id: str) -> Format:
    try:
        return _FORMATS[format_id]
    except KeyError:
        raise KeyError(f"Unknown format {format_id!r}") from None


def list_formats() -> list[Format]:
    return list(_FORMATS.values())


def register_format(fmt: Format) -> None:
    _FORMATS[fmt.id] = fmt


def resolve_format_id(raw: str | None) -> str:
    """Map a deck source's declared format string onto a registered format id,
    tolerating spacing/casing/punctuation. Falls back to Duel Commander (the
    only fully-modelled format) for anything unknown or missing."""
    key = re.sub(r"[^a-z0-9]", "", (raw or "").lower())
    if key in _FORMATS:
        return key
    return _FORMAT_ALIASES.get(key, DUEL_COMMANDER.id)


__all__ = [
    "Format", "get_format", "list_formats", "register_format",
    "resolve_format_id", "DUEL_COMMANDER",
]
