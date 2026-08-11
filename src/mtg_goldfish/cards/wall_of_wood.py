"""Wall of Wood — 0/3 Wall, Defender.

Printed keywords are auto (Defender can't attack, others inert with no blockers).
Effectively a fixed body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WallOfWood(Card):
    card_name = "Wall of Wood"
