"""Eddie Brock // Venom, Lethal Protector — Legendary Creature — Human Hero Villain // Legendary Creature — Symbiote Hero Villain.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class EddieBrock(Card):
    card_name = 'Eddie Brock // Venom, Lethal Protector'
