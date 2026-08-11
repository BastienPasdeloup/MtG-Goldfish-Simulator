"""Samite Healer — {1}{W} Creature — Human Cleric 1/1.
{T}: Prevent the next 1 damage that would be dealt to any target this turn.

Model the useful case: {T} adds a 1-damage prevention shield for yourself (any
colour)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class SamiteHealer(Card):
    card_name = "Samite Healer"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []

        def pay(st):
            live = st.find_permanent(perm.uid)
            if live is None or live.tapped or live.summoning_sick:
                return False
            live.tapped = True
            return True

        def resolve(st):
            st.prevent_shields.append((1, None))
            st.emit("Samite Healer: prevent next 1 damage to you this turn")
            return None

        return [CardAction.activated(
            "Samite Healer: {T} — prevent next 1 damage",
            pay, resolve, source_name="Samite Healer",
            ability_text="Prevent the next 1 damage to any target")]
