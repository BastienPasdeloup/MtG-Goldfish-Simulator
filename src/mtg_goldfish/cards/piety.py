"""Piety — {2}{W} Instant.
Blocking creatures get +0/+3 until end of turn.

Only affects BLOCKING creatures; there is no blocking in a solitaire goldfish, so
it's inert. The spell is still cast (counting toward spells cast)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class Piety(Card):
    card_name = "Piety"
