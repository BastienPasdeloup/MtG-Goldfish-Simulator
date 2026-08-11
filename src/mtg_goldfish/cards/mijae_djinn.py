"""Mijae Djinn — {R}{R}{R} Creature — Djinn 6/3.
Whenever this creature attacks, flip a coin. If you lose the flip, remove this
creature from combat and tap it.

A cheap 6/3 attacker with a coin-flip drawback: on attack, a branch — win (attacks
normally) or lose (removed from combat, i.e. deals no combat damage)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class MijaeDjinn(Card):
    card_name = "Mijae Djinn"

    def on_attack(self, state, perm):
        def fn(st, opt):
            if opt == "lose":
                p = st.find_permanent(perm.uid)
                if p is not None and p.uid in st.attackers:
                    st.attackers.remove(p.uid)
                    p.tapped = True
                    st.emit("Mijae Djinn: lost the flip — removed from combat")
            else:
                st.emit("Mijae Djinn: won the flip — attacks")
            return None

        return branch_over(state, ["win", "lose"], fn)
