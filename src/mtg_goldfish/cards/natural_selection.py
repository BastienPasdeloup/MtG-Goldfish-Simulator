"""Natural Selection — {G} Instant.
Look at the top three cards of target player's library, then put them back in any
order. You may have that player shuffle.

Reorders the top three cards of your own library — one branch per distinct
ordering (so the search can set up its next draws)."""
from __future__ import annotations

import itertools

from .base import Card, CardAction
from .registry import register


@register
class NaturalSelection(Card):
    card_name = "Natural Selection"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        k = min(3, len(state.library))
        acts = []
        seen: set[tuple] = set()
        for order in itertools.permutations(range(k)):
            if order in seen:
                continue
            seen.add(order)

            def make(order=order):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    top = st.library[:len(order)]
                    st.library[:len(order)] = [top[j] for j in order]
                    st.mark_known_in_library(*st.library[:len(order)])
                    st.emit("Natural Selection: reorder top of library")
                    return None
                return fn

            label = "cast Natural Selection → keep top order" if order == tuple(range(k)) \
                else f"cast Natural Selection → reorder top {k}"
            acts.append(CardAction(label, make()))
        return acts
