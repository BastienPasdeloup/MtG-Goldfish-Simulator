"""Stasis — {1}{U} Enchantment.
Players skip their untap steps.
At the beginning of your upkeep, sacrifice this enchantment unless you pay {U}.

"Players skip their untap steps" is modelled by holding EVERY permanent tapped in
the untap step (prevents_untap returns True for all while Stasis is in play). Each
of your upkeeps: pay {U} to keep it, else sacrifice it."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class Stasis(Card):
    card_name = "Stasis"
    trigger_phase = Phase.UPKEEP

    def prevents_untap(self, state, source, perm):
        return True  # players skip their untap steps

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("U", 1),))
        if can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Stasis: pay {U} (kept)")
            return None
        p = state.find_permanent(perm.uid)
        if p is not None:
            state.emit("Stasis: didn't pay {U} — sacrifice")
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
