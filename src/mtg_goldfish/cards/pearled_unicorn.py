"""Pearled Unicorn
{2}{W} Creature — Unicorn 2/2. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PearledUnicorn(Card):
    card_name = "Pearled Unicorn"
