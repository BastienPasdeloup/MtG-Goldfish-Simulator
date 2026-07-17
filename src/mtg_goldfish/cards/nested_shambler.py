"""Nested Shambler — {B} Creature 1/1. When it dies, create X tapped 1/1 green
Squirrel creature tokens, where X is this creature's power."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NestedShambler(Card):
    card_name = "Nested Shambler"

    def on_leave(self, state, permanent):
        x = max(0, permanent.base_power() + permanent.counters.get("+1/+1", 0)
                + permanent.temp_power)
        for _ in range(x):
            state.make_token("Squirrel", 1, 1, "Creature — Squirrel", tapped=True)
        state.emit(f"Nested Shambler: create {x} tapped 1/1 Squirrels")
