"""Erg Raiders — {1}{B} Creature — Human Warrior 2/3.
At the beginning of your end step, if this creature didn't attack this turn, it
deals 2 damage to you unless it came under your control this turn.

A cheap beater with a downside: at your end step, if it didn't attack (and it has
been under your control since before this turn — i.e. not summoning-sick), it
pings you 2."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class ErgRaiders(Card):
    card_name = "Erg Raiders"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        p = state.find_permanent(perm.uid)
        if p is None or p.summoning_sick:  # came under control this turn -> no damage
            return None
        if not p.turn_flags.get("attacked"):
            dealt = state.damage_self(2, colors=("B",))
            state.emit(f"Erg Raiders: didn't attack — {dealt} damage to you")
        return None
