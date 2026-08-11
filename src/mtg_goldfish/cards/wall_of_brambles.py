"""Wall of Brambles — 2/3 Plant Wall, Defender.
{G}: Regenerate this creature.

{G} banks a regeneration shield (consumed by the next destroy / lethal
damage — see GameState._survives_destruction). Printed keywords are auto."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class WallOfBrambles(Card):
    card_name = "Wall of Brambles"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("G", 1),))
        if perm.counters.get("regen_shield") or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Wall of Brambles: regeneration shield")
            return None

        return [CardAction.activated(
            "Wall of Brambles: {G} — regenerate",
            pay, resolve, source_name="Wall of Brambles",
            ability_text="Regenerate")]
