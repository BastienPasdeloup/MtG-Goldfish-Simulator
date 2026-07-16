"""Infestation Sage — {B} Creature 1/1. When it dies, create a 1/1 black and
green Insect creature token with flying."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class InfestationSage(Card):
    card_name = "Infestation Sage"

    def on_leave(self, state, permanent):
        state.make_token("Insect", 1, 1, "Creature — Insect", text="Flying")
        state.emit("Infestation Sage: create a 1/1 flying Insect")
