"""Dwarven Warriors
{2}{R} Creature — Dwarf Warrior 1/1. {T}: Target creature with power 2 or
less can't be blocked this turn. Unblockability is irrelevant with no blockers —
a plain 1/1 with a no-op ability."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DwarvenWarriors(Card):
    card_name = "Dwarven Warriors"
