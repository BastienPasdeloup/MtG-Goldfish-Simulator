"""Jennifer Walters // The Sensational She-Hulk — Legendary Creature — Human Advisor Hero // Legendary Creature — Gamma Hero.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class JenniferWalters(Card):
    card_name = 'Jennifer Walters // The Sensational She-Hulk'
