"""Oubliette — {1}{B}{B} Enchantment.
When this enchantment enters, target creature phases out until Oubliette leaves ...

Removal aimed at an opponent's creature; phasing out one of YOUR creatures is only
a downside, so it's inert here. A bare enchantment that still enters (counting as a
permanent)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class Oubliette(Card):
    card_name = "Oubliette"
