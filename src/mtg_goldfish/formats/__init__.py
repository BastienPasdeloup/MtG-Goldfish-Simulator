"""Format registry."""
from __future__ import annotations

import re

from .base import Format
from .duel_commander import DUEL_COMMANDER

_FORMATS: dict[str, Format] = {
    DUEL_COMMANDER.id: DUEL_COMMANDER,
}

#: Aliases mapping a deck source's declared format (normalized to lowercase
#: alphanumerics) onto a registered format id. Every commander variant maps to
#: Duel Commander — the only format the simulator fully models.
_FORMAT_ALIASES = {
    "duelcommander": DUEL_COMMANDER.id,
    "commander": DUEL_COMMANDER.id,
    "commander1v1": DUEL_COMMANDER.id,
    "frenchcommander": DUEL_COMMANDER.id,
    "edh": DUEL_COMMANDER.id,
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
