"""Bog Wraith — {3}{B} Creature — Wraith 3/3. Swampwalk.
Swampwalk (unblockable vs a Swamp-controlling defender) has no effect with no
opponent — a plain 3/3."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BogWraith(Card):
    card_name = "Bog Wraith"
