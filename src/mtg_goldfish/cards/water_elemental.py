"""Water Elemental — 5/4 vanilla Elemental.

Printed keywords are auto (Defender can't attack, others inert with no blockers).
Effectively a fixed body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WaterElemental(Card):
    card_name = "Water Elemental"
