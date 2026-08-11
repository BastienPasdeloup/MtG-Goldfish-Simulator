"""Wall of Stone — 0/8 Wall, Defender.

Printed keywords are auto (Defender can't attack, others inert with no blockers).
Effectively a fixed body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WallOfStone(Card):
    card_name = "Wall of Stone"
