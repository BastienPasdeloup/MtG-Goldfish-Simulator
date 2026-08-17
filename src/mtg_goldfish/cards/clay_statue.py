"""Clay Statue — {4} Artifact Creature — Golem 3/1.
{2}: Regenerate this creature.

{2} banks a regeneration shield (consumed by the next destroy / lethal damage —
see GameState._survives_destruction)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ClayStatue(Card):
    card_name = "Clay Statue"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Clay Statue: regeneration shield")
            return None

        return [CardAction.activated(
            "Clay Statue: {2} — regenerate",
            pay, resolve, source_name="Clay Statue",
            ability_text="Regenerate")]
