"""Wall of Swords — 3/5 Wall, Defender+Flying.

Printed keywords are auto (Defender can't attack, others inert with no blockers).
Effectively a fixed body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WallOfSwords(Card):
    card_name = "Wall of Swords"
