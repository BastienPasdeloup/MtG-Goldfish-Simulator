"""Superior Spider-Man — {2}{U}{B} Legendary 4/4. Mind Swap: may enter as a
copy of any creature card in a graveyard (exiling it), except he stays a 4/4
named Superior Spider-Man. Branches over each graveyard creature + entering
normally. Approximation: the copied card's *abilities* are not adopted (P/T
and types stay 4/4 Spider Hero per the card, so board-state queries are exact)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class SuperiorSpiderMan(Card):
    card_name = "Superior Spider-Man"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_battlefield

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def make(copy_name: str | None):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                if copy_name is not None:
                    gy = next((c for c in st.graveyard if c.name == copy_name), None)
                    if gy is not None:
                        st.graveyard.remove(gy)
                        st.exile.append(gy)
                        st.emit(f"Mind Swap: enters as a copy of {copy_name} (exiled)")
                return resolve_to_battlefield(st, card) or None
            return fn

        actions = [CardAction("cast Superior Spider-Man", make(None))]
        for name in sorted({c.name for c in state.graveyard if c.is_creature}):
            actions.append(CardAction(f"cast Superior Spider-Man (copy {name})", make(name)))
        return actions
