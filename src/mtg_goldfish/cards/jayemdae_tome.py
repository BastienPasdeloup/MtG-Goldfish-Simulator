"""Jayemdae Tome — {4} Artifact — Book.
{4}, {T}: Draw a card.

A repeatable card-draw engine: {4}, {T} to draw one (real card advantage)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class JayemdaeTome(Card):
    card_name = "Jayemdae Tome"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=4)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.draw(1)
            st.emit("Jayemdae Tome: draw a card")
            return None

        return [CardAction.activated(
            "Jayemdae Tome: {4}, {T} — draw a card",
            pay, resolve, source_name="Jayemdae Tome",
            ability_text="Draw a card")]
