"""Shivan Dragon — {4}{R}{R} Creature — Dragon 5/5. Flying.
{R}: This creature gets +1/+0 until end of turn.

Firebreathing on itself (temp +1/+0 per {R}), plus flying (auto from keyword)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ShivanDragon(Card):
    card_name = "Shivan Dragon"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.temp_power += 1
                st.emit("Shivan Dragon: +1/+0 until end of turn")
            return None

        return [CardAction.activated(
            "Shivan Dragon: {R} — +1/+0 until end of turn",
            pay, resolve, source_name="Shivan Dragon",
            ability_text="+1/+0 until end of turn")]
