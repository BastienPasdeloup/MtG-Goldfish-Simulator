"""Mana Vault — {1} Artifact.
This artifact doesn't untap during your untap step.
At the beginning of your upkeep, you may pay {4}. If you do, untap this artifact.
At the beginning of your draw step, if this artifact is tapped, it deals 1 damage
to you.
{T}: Add {C}{C}{C}.

Taps for three colourless, stays tapped through untap (skips_untap). Two phase
triggers: on your upkeep a branch to pay {4} and untap it; on your draw step it
pings you 1 if still tapped. Uses a custom phase_stack_items gated to those two
phases (trigger_phase can only name one)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class ManaVault(Card):
    card_name = "Mana Vault"

    def skips_untap(self, state, perm):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=3, choices=("C",))]

    def phase_stack_items(self, state, perm, phase):
        if phase not in (Phase.UPKEEP, Phase.DRAW):
            return []
        return super().phase_stack_items(state, perm, phase)

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        p = state.find_permanent(perm.uid)
        if p is None:
            return None
        if phase == Phase.DRAW:
            if p.tapped:
                dealt = state.damage_self(1)
                state.emit(f"Mana Vault: {dealt} damage to you (still tapped)")
            return None
        # UPKEEP: may pay {4} to untap (only meaningful while tapped)
        if not p.tapped:
            return None
        cost = ManaCost(generic=4)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            live = st.find_permanent(perm.uid)
            if opt == "untap" and live is not None and live.tapped and pay_cost(st, cost):
                live.tapped = False
                st.emit("Mana Vault: pay {4}, untap")
            return None

        return branch_over(state, ["decline", "untap"], fn)
