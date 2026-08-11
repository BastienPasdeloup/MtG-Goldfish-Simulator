"""Jandor's Ring — {6} Artifact.
{2}, {T}, Discard the last card you drew this turn: Draw a card.

Modelled as rummage: {2}, {T}, discard a card from hand → draw a card (the "last
drawn" restriction isn't tracked; discarding any card is a safe under-approximation
— one branch per discard choice, each drawing one)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class JandorsRing(Card):
    card_name = "Jandor's Ring"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not state.hand or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not st.hand or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            seen: set[str] = set()
            opts = []
            for c in st.hand:
                if c.name not in seen:
                    seen.add(c.name)
                    opts.append(c.name)

            def fn(s, name):
                card = next((c for c in s.hand if c.name == name), None)
                if card is not None:
                    s.discard(card)
                    s.draw(1)
                    s.emit(f"Jandor's Ring: discard {name}, draw a card")
                return None

            return st.settle(branch_over(st, opts, fn))

        return [CardAction.activated(
            "Jandor's Ring: {2}, {T}, discard a card — draw a card",
            pay, resolve, source_name="Jandor's Ring",
            ability_text="Discard a card, then draw a card")]
