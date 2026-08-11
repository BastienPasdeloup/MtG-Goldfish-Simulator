"""Blessing — {W}{W} Enchantment — Aura. Enchant creature.
{W}: Enchanted creature gets +1/+1 until end of turn.

Cast onto one of your creatures (one branch each); the pump is an activated
ability on the Aura targeting its host (temp +1/+1, cleared at cleanup)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import aura_enchant_actions
from .base import Card, CardAction
from .registry import register


@register
class Blessing(Card):
    card_name = "Blessing"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}{W}")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        cost = ManaCost(pips=(("W", 1),))
        if host is None or not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            h = st.find_permanent(perm.attached_to)
            if h is not None:
                h.temp_power += 1
                h.temp_toughness += 1
                st.emit(f"Blessing: {h.name} gets +1/+1 until end of turn")
            return None

        return [CardAction.activated(
            "Blessing: {W} — enchanted creature +1/+1 until end of turn",
            pay, resolve, source_name="Blessing",
            ability_text="Enchanted creature gets +1/+1 until end of turn")]
