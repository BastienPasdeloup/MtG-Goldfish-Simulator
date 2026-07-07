"""Gwen Stacy // Ghost-Spider — Legendary Creature — Human Performer Hero // Legendary Creature — Spider Human Hero.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GwenStacy(Card):
    card_name = 'Gwen Stacy // Ghost-Spider'
