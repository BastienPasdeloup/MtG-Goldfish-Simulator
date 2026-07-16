"""Cult Conscript — {B} Creature 2/1, enters tapped.
{1}{B}: Return this card from your graveyard to the battlefield. Activate only if
a non-Skeleton creature died under your control this turn."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


def _nonskeleton_died(state) -> bool:
    for e in state.events:
        if (e["turn"] == state.turn and e["kind"] == "leave_battlefield"
                and e.get("is_creature") and e.get("to") == "graveyard"):
            c = e.get("card")
            if c is not None and "skeleton" not in c.type_line.lower():
                return True
    return False


@register
class CultConscript(Card):
    card_name = "Cult Conscript"

    def etb_tapped(self, state):
        return True

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("B", 1),))
        if not _nonskeleton_died(state) or not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None or not _nonskeleton_died(st) or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None:
                return None
            st.graveyard.remove(card)
            enter_battlefield(st, card, tapped=True,
                              announce="Cult Conscript returns tapped")
            return None

        return [CardAction.activated(
            "return Cult Conscript from graveyard",
            pay, resolve,
            source_name=self.card_name,
            ability_text="Return Cult Conscript from your graveyard",
        )]
