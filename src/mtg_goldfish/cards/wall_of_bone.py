"""Wall of Bone — 1/4 Skeleton Wall, Defender.
{B}: Regenerate this creature.

{B} banks a regeneration shield (consumed by the next destroy / lethal
damage — see GameState._survives_destruction). Printed keywords are auto."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class WallOfBone(Card):
    card_name = "Wall of Bone"

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
                st.emit("Wall of Bone: regeneration shield")
            return None

        return [CardAction.activated(
            "Wall of Bone: {B} — regenerate",
            pay, resolve, source_name="Wall of Bone",
            ability_text="Regenerate")]
