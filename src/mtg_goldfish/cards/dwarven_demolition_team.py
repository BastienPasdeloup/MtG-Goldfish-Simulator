"""Dwarven Demolition Team
{2}{R} Creature — Dwarf 1/1. {T}: Destroy target Wall.
Only an opponent's Wall is worth destroying (none in a goldfish) — a plain 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DwarvenDemolitionTeam(Card):
    card_name = "Dwarven Demolition Team"
