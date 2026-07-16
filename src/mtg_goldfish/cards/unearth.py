"""Unearth — {B} Sorcery. Return target creature card with mana value 3 or less
from your graveyard to the battlefield. Cycling {2}."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over, enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class Unearth(Card):
    card_name = "Unearth"

    def on_resolve(self, state):
        targets = {c.name for c in state.graveyard
                   if c.is_creature and c.cmc <= 3}
        if not targets:
            return None

        def fn(st, name):
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is None:
                return None
            st.leave_graveyard(c)
            enter_battlefield(st, c, announce=f"Unearth: return {name} to battlefield")
            return None

        return branch_over(state, sorted(targets), fn)

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, cost):
                return False
            st.discard(card)
            return True

        def resolve(st):
            st.draw(1)
            st.emit("Unearth: cycling — draw a card")
            return None

        return [CardAction.activated(
            "Unearth: cycling {2}", pay, resolve,
            source_name="Unearth", ability_text="Cycling")]
