"""Night Nurse, Healer of Heroes — Legendary Creature — Human Doctor Hero.

Best-effort implementation: the engine models this card being cast/entering and
counting toward board state and spell tallies, but its special rules text is not
simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NightNurseHealerOfHeroes(Card):
    card_name = 'Night Nurse, Healer of Heroes'
