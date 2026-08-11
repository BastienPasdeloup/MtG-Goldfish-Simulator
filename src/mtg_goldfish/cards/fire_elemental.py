"""Fire Elemental
{3}{R}{R} Creature — Elemental 5/4. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class FireElemental(Card):
    card_name = "Fire Elemental"
