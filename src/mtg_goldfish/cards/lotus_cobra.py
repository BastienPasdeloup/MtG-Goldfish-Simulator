"""Lotus Cobra — {1}{G} Creature — Snake 2/1.
Landfall: add one mana of any color (identity — goes to the pool, usable
this phase; the payment planner does not anticipate it)."""
from __future__ import annotations

from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class LotusCobra(Card):
    card_name = "Lotus Cobra"

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            color = any_identity_color(state)[0]
            state.mana_pool.add(color, 1)
            state.emit(f"Lotus Cobra: landfall — add {{{color}}}")
