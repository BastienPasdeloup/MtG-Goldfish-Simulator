"""Magical Hack — {U} Instant.
Change the text of target spell or permanent by replacing all instances of one
basic land type with another.

A text-changing trick that only matters for landwalk/land-type interactions,
which are inert in a solitaire goldfish. The spell is still cast (counting toward
spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MagicalHack(Card):
    card_name = "Magical Hack"
