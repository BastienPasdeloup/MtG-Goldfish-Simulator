"""Brass Man — {1} Artifact Creature — Construct 1/3.
This creature doesn't untap during your untap step.
At the beginning of your upkeep, you may pay {1}. If you do, untap this creature.

A cheap 1/3 that stays tapped once it taps (skips_untap) unless you pay {1} at your
upkeep to untap it."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class BrassMan(Card):
    card_name = "Brass Man"
    trigger_phase = Phase.UPKEEP

    def skips_untap(self, state, perm):
        return True

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        p = state.find_permanent(perm.uid)
        if p is None or not p.tapped:
            return None
        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            live = st.find_permanent(perm.uid)
            if opt == "untap" and live is not None and live.tapped and pay_cost(st, cost):
                live.tapped = False
                st.emit("Brass Man: pay {1}, untap")
            return None

        return branch_over(state, ["decline", "untap"], fn)
