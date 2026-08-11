"""Hurr Jackal — {R} Creature — Jackal 1/1.
{T}: Target creature can't be regenerated this turn.

Anti-regeneration is only useful against a creature you're about to destroy —
opponent-facing in practice — so the ability is inert. A 1/1 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HurrJackal(Card):
    card_name = "Hurr Jackal"
