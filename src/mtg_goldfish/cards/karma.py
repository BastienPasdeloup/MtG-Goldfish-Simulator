"""Karma — {2}{W}{W} Enchantment.
At the beginning of each player's upkeep, this enchantment deals damage to that
player equal to the number of Swamps they control.

Symmetric — on each of YOUR upkeeps it deals you damage equal to your Swamp count
(via damage_self, so prevention applies). Zero in a non-Swamp deck."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class Karma(Card):
    card_name = "Karma"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        swamps = sum(1 for p in state.battlefield
                     if p.is_land and "swamp" in p.type_line.lower())
        if swamps:
            dealt = state.damage_self(swamps, colors=("W",))
            state.emit(f"Karma: {dealt} damage to you ({swamps} Swamps)")
        return None
