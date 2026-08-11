"""Bird Maiden
{2}{R} Creature — Human Bird 1/2. Flying.

Flying is auto from the keyword; otherwise a vanilla 1/2."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BirdMaiden(Card):
    card_name = "Bird Maiden"
