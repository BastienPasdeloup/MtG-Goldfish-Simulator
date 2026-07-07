"""Basim Ibn Ishaq — Legendary Creature — Human Assassin.

Best-effort implementation: the engine models this card being cast/entering and
counting toward board state and spell tallies, but its special rules text is not
simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BasimIbnIshaq(Card):
    card_name = 'Basim Ibn Ishaq'
