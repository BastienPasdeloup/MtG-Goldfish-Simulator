"""Air Elemental — {3}{U}{U} Creature — Elemental 4/4. Flying.
Vanilla flyer; the engine reads Flying from the card data."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AirElemental(Card):
    card_name = "Air Elemental"
