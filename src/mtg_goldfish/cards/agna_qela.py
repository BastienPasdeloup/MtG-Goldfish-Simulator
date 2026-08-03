"""Agna Qel'a — Land. Enters tapped unless you control a basic land.
{T}: Add {U}. {2}{U}, {T}: Draw a card, then discard a card."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import loot
from .base import Card, CardAction
from .registry import register

_LOOT_COST = ManaCost(generic=2, pips=(("U", 1),))


@register
class AgnaQela(Card):
    card_name = "Agna Qel'a"

    def etb_tapped(self, state):
        return not any(p.is_land and "basic" in p.type_line.lower()
                       for p in state.battlefield)

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped or not can_afford(state, _LOOT_COST, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, _LOOT_COST, exclude_uids={p.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            return loot(st, 1, 1, source="Agna Qel'a")

        return [CardAction.activated(
            "Agna Qel'a: {2}{U}, {T}: loot", pay, resolve,
            source_name="Agna Qel'a", ability_text="Draw a card, then discard a card")]
