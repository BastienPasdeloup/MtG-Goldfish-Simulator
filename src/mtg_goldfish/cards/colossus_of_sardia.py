"""Colossus of Sardia — {9} Artifact Creature — Golem 9/9, Trample.
This creature doesn't untap during your untap step.
{9}: Untap this creature. Activate only during your upkeep.

Trample is auto; it stays tapped through the untap step (`skips_untap`) and can
only be re-untapped for {9} during your upkeep."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ColossusOfSardia(Card):
    card_name = "Colossus of Sardia"

    def skips_untap(self, state, perm):
        return True

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if not perm.tapped or state.phase != Phase.UPKEEP:
            return []
        cost = ManaCost(generic=9)
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.tapped = False
                st.emit("Colossus of Sardia: untap")
            return None

        return [CardAction.activated(
            "Colossus of Sardia: {9} — untap",
            pay, resolve, source_name="Colossus of Sardia",
            ability_text="Untap this creature")]
