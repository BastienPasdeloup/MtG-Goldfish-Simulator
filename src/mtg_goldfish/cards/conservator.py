"""Conservator — {4} Artifact.
{3}, {T}: Prevent the next 2 damage that would be dealt to you this turn.

Adds a colourless prevention shield (matches any source) via GameState —
prevents self-damage from Ankh, Copper Tablet, etc."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Conservator(Card):
    card_name = "Conservator"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.prevent_shields.append((2, None))
            st.emit("Conservator: prevent the next 2 damage to you this turn")
            return None

        return [CardAction.activated(
            "Conservator: {3}, {T} — prevent the next 2 damage to you",
            pay, resolve, source_name="Conservator",
            ability_text="Prevent the next 2 damage to you this turn")]
