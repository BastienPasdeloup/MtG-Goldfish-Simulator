"""Onulet — {3} Artifact Creature — Construct 2/2.
When this creature dies, you gain 2 life.

`on_leave` is the engine's "when this dies" hook (a goldfish creature leaves the
battlefield essentially only by dying)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Onulet(Card):
    card_name = "Onulet"

    def on_leave(self, state, permanent):
        state.gain_life(2)
        state.emit(f"Onulet dies: gain 2 life ({state.life})")
