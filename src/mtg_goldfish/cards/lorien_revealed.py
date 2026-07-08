"""Lórien Revealed — {3}{U}{U} Sorcery: draw three cards.
Islandcycling {1}: discard this card, search your library for an Island card
(any land with the Island subtype), put it into your hand, then shuffle."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import has_subtype
from .base import Card, CardAction
from .registry import register


@register
class LorienRevealed(Card):
    card_name = "Lórien Revealed"

    def on_resolve(self, state):
        state.draw(3)
        state.emit(f"Lórien Revealed: draw 3 ({len(state.hand)} in hand)")
        return None

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return []
        islands = state.search_library(lambda c: c.is_land and has_subtype(c, ("Island",)))

        def make(target_name: str | None):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not pay_cost(st, cost):
                    return None
                st.hand.remove(card)
                st.to_graveyard(card)
                if target_name is not None:
                    t = next((c for c in st.library if c.name == target_name), None)
                    if t is not None:
                        st.take_from_library(t)
                        st.hand.append(t)
                st.shuffle_library()
                st.emit(f"islandcycle Lórien Revealed → {target_name or 'no Island found'}")
                return None
            return fn

        if not islands:
            return [CardAction("islandcycle Lórien Revealed (whiff)", make(None))]
        return [CardAction(f"islandcycle Lórien Revealed → {c.name}", make(c.name)) for c in islands]
