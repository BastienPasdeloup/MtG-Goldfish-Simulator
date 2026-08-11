"""Sandstorm — {G} Instant.
Sandstorm deals 1 damage to each attacking creature.

Only hits ATTACKING creatures — your own, in a solitaire goldfish — so it's never
worth casting. The spell is still cast (counting toward spells cast)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class Sandstorm(Card):
    card_name = "Sandstorm"
