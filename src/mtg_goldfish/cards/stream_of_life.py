"""Stream of Life — {X}{G} Sorcery. Target player gains X life.

You gain X life (one branch per affordable X)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class StreamOfLife(Card):
    card_name = "Stream of Life"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(1, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("G", 1),))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    st.life += xx
                    st.emit(f"Stream of Life: gain {xx} life")
                    return None
                return fn

            acts.append(CardAction(f"cast Stream of Life (X={x}) → gain {x} life", make(x)))
        return acts
