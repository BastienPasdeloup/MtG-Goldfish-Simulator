"""Frozen Shade — {2}{B} Creature — Shade 0/1.
{B}: This creature gets +1/+1 until end of turn.

A mana-sink pump on the creature itself (temp +1/+1 per activation) — the classic
Shade. Repeatable as long as you can pay {B}."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class FrozenShade(Card):
    card_name = "Frozen Shade"

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
                p.temp_power += 1
                p.temp_toughness += 1
                st.emit("Frozen Shade: +1/+1 until end of turn")
            return None

        return [CardAction.activated(
            "Frozen Shade: {B} — +1/+1 until end of turn",
            pay, resolve, source_name="Frozen Shade",
            ability_text="+1/+1 until end of turn")]
