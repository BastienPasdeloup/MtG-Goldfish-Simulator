"""Wall of Air
{1}{U}{U} Creature — Wall 1/5. Defender, flying.

Both keywords are auto from the printed keywords (Defender can't attack, flying is
inert with no attackers to block). A 1/5 defensive body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WallOfAir(Card):
    card_name = "Wall of Air"
