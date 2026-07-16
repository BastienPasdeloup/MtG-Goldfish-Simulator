"""Bloodsoaked Champion — {B} Creature 2/1, can't block.
Raid — {1}{B}: Return this card from your graveyard to the battlefield. Activate
only if you attacked this turn."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class BloodsoakedChampion(Card):
    card_name = "Bloodsoaked Champion"

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("B", 1),))
        if not state.attacked_this_turn or not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None or not st.attacked_this_turn or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None:
                return None
            st.graveyard.remove(card)
            enter_battlefield(st, card, announce="Bloodsoaked Champion returns (raid)")
            return None

        return [CardAction.activated(
            "raid: return Bloodsoaked Champion from graveyard",
            pay, resolve,
            source_name=self.card_name,
            ability_text="Return Bloodsoaked Champion from your graveyard",
        )]
