"""Living Wall — {4} Artifact Creature — Wall 0/6. Defender.
{1}: Regenerate this creature.

Defender is auto (it can't attack). {1} banks a regeneration shield (consumed by
the next destroy / lethal damage — see GameState._survives_destruction)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class LivingWall(Card):
    card_name = "Living Wall"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Living Wall: regeneration shield")
            return None

        return [CardAction.activated(
            "Living Wall: {1} — regenerate",
            pay, resolve, source_name="Living Wall",
            ability_text="Regenerate")]
