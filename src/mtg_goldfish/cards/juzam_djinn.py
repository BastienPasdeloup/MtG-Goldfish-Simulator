"""Juzám Djinn — {2}{B}{B} Creature — Djinn 5/5.
At the beginning of your upkeep, this creature deals 1 damage to you.

A big cheap beater with an upkeep ping: 1 damage to you each of your upkeeps."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class JuzamDjinn(Card):
    card_name = "Juzám Djinn"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        dealt = state.damage_self(1, colors=("B",))
        state.emit(f"Juzám Djinn: {dealt} damage to you")
        return None
