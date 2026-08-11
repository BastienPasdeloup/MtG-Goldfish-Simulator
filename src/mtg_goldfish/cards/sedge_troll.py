"""Sedge Troll — {2}{R} Creature — Troll 2/2. Regenerate.
This creature gets +1/+1 as long as you control a Swamp.
{B}: Regenerate this creature.

The +1/+1 is a self-anthem via static_pt_bonus (applies only to itself, only while
you control a Swamp). {B} banks a regeneration shield."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class SedgeTroll(Card):
    card_name = "Sedge Troll"

    def static_pt_bonus(self, state, source, perm):
        if perm.uid == source.uid and any(
                p.is_land and "swamp" in p.type_line.lower() for p in state.battlefield):
            return (1, 1)
        return (0, 0)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        if perm.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Sedge Troll: regeneration shield")
            return None

        return [CardAction.activated(
            "Sedge Troll: {B} — regenerate",
            pay, resolve, source_name="Sedge Troll",
            ability_text="Regenerate")]
