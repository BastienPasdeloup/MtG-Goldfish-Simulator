"""Power Surge — {R}{R} Enchantment.
At the beginning of each player's upkeep, this enchantment deals X damage to that
player, where X is the number of untapped lands they controlled at the beginning
of this turn.

Symmetric — on your upkeep it deals you damage equal to your untapped-land count
(via damage_self, red source). Approximated with the untapped-land count at the
moment of the upkeep trigger. Punishes flooding untapped lands."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class PowerSurge(Card):
    card_name = "Power Surge"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        x = sum(1 for p in state.battlefield if p.is_land and not p.tapped)
        if x:
            dealt = state.damage_self(x, colors=("R",))
            state.emit(f"Power Surge: {dealt} damage to you ({x} untapped lands)")
        return None
