"""Su-Chi — {4} Artifact Creature — Construct 4/4.
When this creature dies, add {C}{C}{C}{C}.

Four colourless into the pool on death (`on_leave` = the "dies" hook)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SuChi(Card):
    card_name = "Su-Chi"

    def on_leave(self, state, permanent):
        state.mana_pool.add("C", 4)
        state.emit("Su-Chi dies: add {C}{C}{C}{C}")
