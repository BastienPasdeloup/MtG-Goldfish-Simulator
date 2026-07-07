"""The Wondrous Wasp — Legendary Creature — Human Hero.

Best-effort implementation: the engine models this card being cast/entering and
counting toward board state and spell tallies, but its special rules text is not
simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TheWondrousWasp(Card):
    card_name = 'The Wondrous Wasp'
