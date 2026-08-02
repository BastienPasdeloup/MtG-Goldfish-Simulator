"""Gau, Feral Youth — {1}{R} Legendary Creature 2/2.
Rage — Whenever Gau attacks, put a +1/+1 counter on it.
At the beginning of each end step, if a card left your graveyard this turn, Gau
deals damage equal to its power to each opponent."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class GauFeralYouth(Card):
    card_name = "Gau, Feral Youth"
    trigger_phase = Phase.END_STEP

    def on_attack(self, state, perm):
        perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
        state.emit(f"Gau: rage +1/+1 "
                   f"({state.effective_power(perm)}/{state.effective_toughness(perm)})")

    def on_phase(self, state, perm, phase):
        if not state.left_graveyard_this_turn:
            return
        dmg = state.effective_power(perm)
        if dmg <= 0:
            return
        state.damage_opponent(dmg)  # noncombat -> amplifiers apply
        state.emit(f"Gau: {dmg} damage to each opponent ({state.opponent_life})")
