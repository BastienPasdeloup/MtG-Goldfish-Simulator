"""Nether Shadow — {B}{B} Creature — Spirit 1/1. Haste.
At the beginning of your upkeep, if this card is in your graveyard with three or
more creature cards above it, you may put this card onto the battlefield.

The graveyard-return trigger fires from the graveyard-upkeep sweep: if there are
≥3 creature cards above Nether Shadow (nearer the top / later in the graveyard
list), it returns to the battlefield. The "may" is auto-taken (a free recurring
1/1 haste is always wanted here)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NetherShadow(Card):
    card_name = "Nether Shadow"

    def graveyard_upkeep(self, state, card, gy_index):
        if card not in state.graveyard:
            return
        above = state.graveyard[gy_index + 1:]
        creatures_above = sum(1 for c in above if "creature" in (c.type_line or "").lower())
        if creatures_above >= 3:
            state.graveyard.remove(card)
            state.put_on_battlefield(card, fire_etb=True)
            state.emit("Nether Shadow: return from graveyard (3+ creatures above)")
