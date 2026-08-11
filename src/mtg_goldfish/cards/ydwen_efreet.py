"""Ydwen Efreet
{R}{R}{R} Creature — Efreet 3/6.
Whenever this creature blocks, flip a coin ...

The coin-flip drawback only triggers on BLOCKING, which never happens in a
solitaire goldfish, so it's inert. A cheap 3/6 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class YdwenEfreet(Card):
    card_name = "Ydwen Efreet"
