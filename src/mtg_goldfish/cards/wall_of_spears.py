"""Wall of Spears — {3} Artifact Creature — Wall 2/3, Defender, First strike.

Printed keywords are auto (Defender can't attack; first strike only matters when
blocking — inert in a goldfish). A fixed body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WallOfSpears(Card):
    card_name = "Wall of Spears"
