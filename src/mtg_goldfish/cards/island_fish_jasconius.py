"""Island Fish Jasconius — {4}{U}{U}{U} Creature — Fish 6/8.
This creature doesn't untap during your untap step.
At the beginning of your upkeep, you may pay {U}{U}{U}. If you do, untap it.
This creature can't attack unless defending player controls an Island.
When you control no Islands, sacrifice this creature.

A 6/8 that stays tapped (skips_untap) unless you pay {U}{U}{U} at upkeep. It can't
attack (no opponent Island) and is sacrificed if you control no Island."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class IslandFishJasconius(Card):
    card_name = "Island Fish Jasconius"
    trigger_phase = Phase.UPKEEP

    def skips_untap(self, state, perm):
        return True

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        p = state.find_permanent(perm.uid)
        if p is None:
            return None
        if not any(q.is_land and "island" in q.type_line.lower() for q in state.battlefield):
            state.emit("Island Fish Jasconius: no Island — sacrifice")
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return None
        cost = ManaCost(pips=(("U", 1), ("U", 1), ("U", 1)))
        if not p.tapped or not can_afford(state, cost):
            return None

        def fn(st, opt):
            live = st.find_permanent(perm.uid)
            if opt == "untap" and live is not None and live.tapped and pay_cost(st, cost):
                live.tapped = False
                st.emit("Island Fish Jasconius: pay {U}{U}{U}, untap")
            return None

        return branch_over(state, ["decline", "untap"], fn)
