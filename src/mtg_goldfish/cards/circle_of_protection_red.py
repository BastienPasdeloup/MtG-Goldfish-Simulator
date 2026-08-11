"""Circle of Protection: Red
{1}{W} Enchantment — {1}: prevent damage from a red source. No effect (no opponent damage)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CircleOfProtectionRed(Card):
    card_name = "Circle of Protection: Red"
