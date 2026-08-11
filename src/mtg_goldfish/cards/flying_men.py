"""Flying Men
{U} Creature — Human 1/1. Flying. Vanilla flyer."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class FlyingMen(Card):
    card_name = "Flying Men"
