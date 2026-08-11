"""Circle of Protection: White
{1}{W} Enchantment — {1}: prevent damage from a white source. No effect (no opponent damage)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CircleOfProtectionWhite(Card):
    card_name = "Circle of Protection: White"
