"""King T'Challa // Black Panther, Hope Enduring — Legendary Creature — Human Noble Hero // Legendary Creature — Human Warrior Hero.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class KingTChalla(Card):
    card_name = "King T'Challa // Black Panther, Hope Enduring"
