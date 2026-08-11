"""Earth Elemental
{3}{R}{R} Creature — Elemental 4/5. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class EarthElemental(Card):
    card_name = "Earth Elemental"
