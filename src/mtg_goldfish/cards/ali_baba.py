"""Ali Baba — {R} Creature — Human Rogue 1/1.
{R}: Tap target Wall.

Tapping a Wall only matters against an opponent's blocker; your own Walls gain
nothing from being tapped, so the ability is inert. A 1/1 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AliBaba(Card):
    card_name = "Ali Baba"
