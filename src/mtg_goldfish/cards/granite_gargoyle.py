"""Granite Gargoyle — {2}{R} Creature — Gargoyle 2/2. Flying.
{R}: This creature gets +0/+1 until end of turn.

A flyer with a repeatable toughness pump on itself (temp +0/+1 per {R})."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class GraniteGargoyle(Card):
    card_name = "Granite Gargoyle"

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
                p.temp_toughness += 1
                st.emit("Granite Gargoyle: +0/+1 until end of turn")
            return None

        return [CardAction.activated(
            "Granite Gargoyle: {R} — +0/+1 until end of turn",
            pay, resolve, source_name="Granite Gargoyle",
            ability_text="+0/+1 until end of turn")]
