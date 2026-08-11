"""Braingeyser — {X}{U}{U} Sorcery.
Target player draws X cards. (Targeting yourself — draw X.) One branch per
affordable X."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Braingeyser(Card):
    card_name = "Braingeyser"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("U", 1), ("U", 1)))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    st.emit(f"Braingeyser: draw {xx} card(s)")
                    st.draw(xx)
                    return None
                return fn

            acts.append(CardAction(f"cast Braingeyser (X={x}) — draw {x}", make(x)))
        return acts
