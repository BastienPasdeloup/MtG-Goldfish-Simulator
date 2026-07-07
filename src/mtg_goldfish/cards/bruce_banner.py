"""Bruce Banner // The Incredible Hulk — Legendary Creature — Human Scientist Hero // Legendary Creature — Gamma Berserker Hero.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BruceBanner(Card):
    card_name = 'Bruce Banner // The Incredible Hulk'
