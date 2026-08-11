"""Cyclone — {2}{G}{G} Enchantment.
At the beginning of your upkeep, put a wind counter on this enchantment, then
sacrifice it unless you pay {G} for each wind counter on it. If you pay, this
enchantment deals damage equal to the number of wind counters to each creature and
each player.

Escalating: each upkeep add a wind counter, then a branch — pay {G}×counters (deal
that much to every creature and player, incl. YOU) or let it be sacrificed."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class Cyclone(Card):
    card_name = "Cyclone"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        p = state.find_permanent(perm.uid)
        if p is None:
            return None
        p.counters["wind"] = p.counters.get("wind", 0) + 1
        n = p.counters["wind"]
        cost = ManaCost(pips=tuple(("G", 1) for _ in range(n)))

        def sacrifice(st):
            live = st.find_permanent(perm.uid)
            if live is not None:
                st.emit("Cyclone: not paid — sacrifice")
                st.leaves_battlefield(live, "graveyard", reason="sacrifice")

        if not can_afford(state, cost):
            sacrifice(state)
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                for q in list(st.battlefield):
                    if q.is_creature_now:
                        st.damage_permanent(q, n)
                st.damage_self(n, colors=("G",))
                st.damage_opponent(n)
                st.note_crime()
                st.emit(f"Cyclone: pay {n}×{{G}}, deal {n} to each creature and player")
                st.check_deaths()
            else:
                sacrifice(st)
            return None

        return branch_over(state, ["sac", "pay"], fn)
