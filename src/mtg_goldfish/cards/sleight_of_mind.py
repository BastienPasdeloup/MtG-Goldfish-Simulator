"""Sleight of Mind — {U} Instant.
Change the text of target spell or permanent by replacing all instances of one
color word with another.

A text-changing trick that only matters for colour-word interactions (protection,
colour-hosers), which are inert in a solitaire goldfish. The spell is still cast
(counting toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SleightOfMind(Card):
    card_name = "Sleight of Mind"
