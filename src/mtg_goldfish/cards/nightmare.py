"""Nightmare — {5}{B} Creature — Nightmare Horse */*. Flying.
Nightmare's power and toughness are each equal to the number of Swamps you
control.

Dynamic P/T = your Swamp count (flying is auto from the keyword)."""
from __future__ import annotations

from .base import Card
from .registry import register


def _swamps(state) -> int:
    return sum(1 for p in state.battlefield
               if p.is_land and "swamp" in p.type_line.lower())


@register
class Nightmare(Card):
    card_name = "Nightmare"

    def dynamic_power(self, state, perm):
        return _swamps(state)

    def dynamic_toughness(self, state, perm):
        return _swamps(state)
