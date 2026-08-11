"""Kaya's Guile — {1}{W}{B} Instant. Choose two — each opponent sacrifices a
creature; exile all opponents' graveyards; create a 1/1 W/B Spirit with flying;
gain 4 life. Entwine {3}. The opponent-facing modes do nothing in a goldfish, so
this makes a Spirit token and gains 4 life."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class KayasGuile(Card):
    card_name = "Kaya's Guile"

    def on_resolve(self, state):
        state.make_token("Spirit", 1, 1, "Creature — Spirit", text="Flying")
        state.gain_life(4)
        state.emit(f"Kaya's Guile: create a 1/1 flying Spirit, gain 4 life ({state.life})")
