"""Disrupting Scepter — {3} Artifact.
{3}, {T}: Target player discards a card. Activate only during your turn.

Aimed at an opponent's hand; targeting yourself discards your own card (a
downside), but the ability is offered — one action, discarding your highest-cost
card."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class DisruptingScepter(Card):
    card_name = "Disrupting Scepter"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if perm.tapped or not state.hand or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
            if st.hand:
                victim = max(st.hand, key=lambda c: (c.cmc, c.name))
                st.discard(victim)
                st.emit(f"Disrupting Scepter: discard {victim.name}")
            return None

        return [CardAction.activated(
            "Disrupting Scepter: {3}, {T} — target player discards",
            pay, resolve, source_name="Disrupting Scepter",
            ability_text="Target player discards a card")]
