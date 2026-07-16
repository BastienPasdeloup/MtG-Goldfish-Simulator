"""Forsaken Miner — {B} Creature 2/2, can't block.
Whenever you commit a crime, you may pay {B}. If you do, return this card from
your graveyard to the battlefield. (Crimes are tracked as targeting an opponent
or their permanents/graveyard — see GameState.note_crime.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class ForsakenMiner(Card):
    card_name = "Forsaken Miner"

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("B", 1),))
        if state.crimes_this_turn <= 0 or not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None or st.crimes_this_turn <= 0 or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None:
                return None
            st.graveyard.remove(card)
            enter_battlefield(st, card, announce="Forsaken Miner returns (crime)")
            return None

        return [CardAction.activated(
            "return Forsaken Miner from graveyard (crime)",
            pay, resolve,
            source_name=self.card_name,
            ability_text="Return Forsaken Miner from your graveyard",
        )]
