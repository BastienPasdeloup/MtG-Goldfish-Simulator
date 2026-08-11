"""Drudge Skeletons — {1}{B} Creature — Skeleton 1/1.
{B}: Regenerate this creature. (Grants a regeneration shield — the next time it
would be destroyed it is saved instead.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DrudgeSkeletons(Card):
    card_name = "Drudge Skeletons"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = p.counters.get("regen_shield", 0) + 1
                st.emit("Drudge Skeletons: regeneration shield")
            return None

        return [CardAction.activated(
            "Drudge Skeletons: {B} — regenerate", pay, resolve,
            source_name="Drudge Skeletons", ability_text="Regenerate this creature")]
