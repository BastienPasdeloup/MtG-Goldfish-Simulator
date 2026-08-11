"""Uthden Troll — {2}{R} Creature — Troll 2/2. Regenerate.
{R}: Regenerate this creature.

{R} banks a regeneration shield (consumed by the next destroy / lethal damage —
see GameState._survives_destruction)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class UthdenTroll(Card):
    card_name = "Uthden Troll"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if perm.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Uthden Troll: regeneration shield")
            return None

        return [CardAction.activated(
            "Uthden Troll: {R} — regenerate",
            pay, resolve, source_name="Uthden Troll",
            ability_text="Regenerate")]
