"""Dragon Engine — {3} Artifact Creature — Construct 1/3.
{2}: This creature gets +1/+0 until end of turn.

Firebreathing-style pump on itself (temp +1/+0 per {2})."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DragonEngine(Card):
    card_name = "Dragon Engine"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.temp_power += 1
                st.emit("Dragon Engine: +1/+0 until end of turn")
            return None

        return [CardAction.activated(
            "Dragon Engine: {2} — +1/+0 until end of turn",
            pay, resolve, source_name="Dragon Engine",
            ability_text="+1/+0 until end of turn")]
