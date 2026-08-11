"""Firebreathing — {R} Enchantment — Aura. Enchant creature.
{R}: Enchanted creature gets +1/+0 until end of turn.

Aura (one branch per creature) + an activated pump on the host (temp +1/+0)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import aura_enchant_actions
from .base import Card, CardAction
from .registry import register


@register
class Firebreathing(Card):
    card_name = "Firebreathing"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{R}")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        cost = ManaCost(pips=(("R", 1),))
        if host is None or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            h = st.find_permanent(perm.attached_to)
            if h is not None:
                h.temp_power += 1
                st.emit(f"Firebreathing: {h.name} +1/+0 until end of turn")
            return None

        return [CardAction.activated(
            "Firebreathing: {R} — enchanted creature +1/+0 until end of turn",
            pay, resolve, source_name="Firebreathing",
            ability_text="+1/+0 until end of turn")]
