"""Thoughtseize — {B} Sorcery. Target player reveals their hand; you choose a
nonland card; that player discards it. You lose 2 life.
Against a phantom opponent the discard does nothing, but you may target YOURSELF
to bin one of your own nonland cards (a real graveyard-enabling line)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class Thoughtseize(Card):
    card_name = "Thoughtseize"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost) or state.life <= 2:
            return []

        def opponent(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            st.note_crime()
            st.life -= 2
            st.emit(f"Thoughtseize: opponent has no revealable hand; lose 2 ({st.life})")
            return None

        actions = [CardAction("cast Thoughtseize → opponent", opponent)]

        # Target yourself: discard one of your own nonland cards, lose 2 life.
        def make_self(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.life -= 2
                victim = next((c for c in st.hand if c.name == name), None)
                if victim is not None:
                    st.discard(victim)
                st.emit(f"Thoughtseize: discard own {name}; lose 2 ({st.life})")
                return None
            return fn

        seen = set()
        for c in state.hand:
            if c.name == self.card_name or c.is_land or c.name in seen:
                continue
            seen.add(c.name)
            actions.append(CardAction(f"cast Thoughtseize → self, discard {c.name}",
                                      make_self(c.name)))
        return actions
