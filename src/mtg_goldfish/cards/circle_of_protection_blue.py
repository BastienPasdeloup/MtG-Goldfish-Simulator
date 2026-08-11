"""Circle of Protection: Blue
{1}{W} Enchantment — {1}: prevent damage from a blue source.
No opponent deals you damage in a goldfish — no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CircleOfProtectionBlue(Card):
    card_name = "Circle of Protection: Blue"
