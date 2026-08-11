"""Fury — {3}{R}{R} Creature 3/3, double strike. Evoke—exile a red card.
When it enters, it deals 4 damage divided as you choose among any number of
target creatures/planeswalkers. In a goldfish the only permanents are yours, so
the choice is "4 damage to one of your creatures" (to trigger deaths) or none;
arbitrary multi-target division is not fully enumerated."""
from __future__ import annotations

from ._common import branch_over, evoke_actions
from .base import Card
from .registry import register


@register
class Fury(Card):
    card_name = "Fury"

    def hand_actions(self, state):
        return evoke_actions(self, state, "R")

    def on_etb(self, state, permanent):
        options = [("no target", None)]
        seen = set()
        for p in state.battlefield:
            if p.is_creature_now and p.uid != permanent.uid and p.name not in seen:
                seen.add(p.name)
                options.append((p.name, p.uid))

        def fn(st, opt):
            suffix, uid = opt
            if uid is None:
                st.emit("Fury: no target for its enter trigger")
                return None
            t = st.find_permanent(uid)
            if t is not None:
                st.damage_permanent(t, 4)
                st.emit(f"Fury: 4 damage to {t.name}")
                st.check_deaths()
            return None

        return branch_over(state, options, fn)
