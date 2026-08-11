"""Serendib Efreet — {2}{U} Creature — Efreet 3/4. Flying.
At the beginning of your upkeep, this creature deals 1 damage to you.

A cheap flying beater with an upkeep ping: 1 damage to you each of your upkeeps."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class SerendibEfreet(Card):
    card_name = "Serendib Efreet"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        dealt = state.damage_self(1, colors=("U",))
        state.emit(f"Serendib Efreet: {dealt} damage to you")
        return None
