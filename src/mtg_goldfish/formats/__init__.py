"""Format registry."""
from __future__ import annotations

from .base import Format
from .duel_commander import DUEL_COMMANDER

_FORMATS: dict[str, Format] = {
    DUEL_COMMANDER.id: DUEL_COMMANDER,
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


__all__ = ["Format", "get_format", "list_formats", "register_format", "DUEL_COMMANDER"]
