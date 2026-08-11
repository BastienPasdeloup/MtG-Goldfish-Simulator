"""Holy Armor — {W} Enchantment — Aura. Enchant creature.
Enchanted creature gets +0/+2.
{W}: Enchanted creature gets +0/+1 until end of turn.

Static +0/+2 via equip_mod, plus a repeatable {W} toughness pump on the host
(temp +0/+1) offered from the Aura."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import aura_enchant_actions
from .base import Card, CardAction
from .registry import register


@register
class HolyArmor(Card):
    card_name = "Holy Armor"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")

    def equip_mod(self, state, perm):
        return (0, 2)

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
                h.temp_toughness += 1
                st.emit(f"Holy Armor: {h.name} +0/+1 until end of turn")
            return None

        return [CardAction.activated(
            "Holy Armor: {W} — enchanted creature +0/+1 until end of turn",
            pay, resolve, source_name="Holy Armor",
            ability_text="+0/+1 until end of turn")]
