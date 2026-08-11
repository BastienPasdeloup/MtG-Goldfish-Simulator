"""Erhnam Djinn — {3}{G} Creature — Djinn 4/5.
At the beginning of your upkeep, target non-Wall creature an opponent controls
gains forestwalk until your next upkeep.

The upkeep drawback only affects an OPPONENT's creature — there are none in a
solitaire goldfish, so it's inert. Effectively a 4/5 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ErhnamDjinn(Card):
    card_name = "Erhnam Djinn"
