"""Circle of Protection: Green
{1}{W} Enchantment — {1}: prevent damage from a green source. No effect (no opponent damage)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CircleOfProtectionGreen(Card):
    card_name = "Circle of Protection: Green"
