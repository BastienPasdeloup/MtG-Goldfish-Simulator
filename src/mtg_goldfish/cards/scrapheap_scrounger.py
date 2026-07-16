"""Scrapheap Scrounger — {2} Artifact Creature 3/2, can't block.
{1}{B}, Exile another creature card from your graveyard: Return this card from
your graveyard to the battlefield. (The exiled creature card is chosen
deterministically — the lowest-mana-value one — rather than branched.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class ScrapheapScrounger(Card):
    card_name = "Scrapheap Scrounger"

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("B", 1),))
        fodder = [c for c in state.graveyard
                  if c.is_creature and c.name != self.card_name]
        if not fodder or not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            fuel = sorted((c for c in st.graveyard
                           if c.is_creature and c.name != self.card_name),
                          key=lambda c: c.cmc)
            if card is None or not fuel or not pay_cost(st, cost):
                return False
            exiled = fuel[0]
            st.graveyard.remove(exiled)
            st.exile.append(exiled)
            st.emit(f"Scrapheap Scrounger: exile {exiled.name} from graveyard")
            return True

        def resolve(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None:
                return None
            st.graveyard.remove(card)
            enter_battlefield(st, card, announce="Scrapheap Scrounger returns")
            return None

        return [CardAction.activated(
            "return Scrapheap Scrounger from graveyard",
            pay, resolve,
            source_name=self.card_name,
            ability_text="Return Scrapheap Scrounger from your graveyard",
        )]
