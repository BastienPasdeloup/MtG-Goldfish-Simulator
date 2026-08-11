"""Earthquake — {X}{R} Sorcery.
Deals X damage to each creature without flying and each player.

Symmetric burn: X to the opponent, X to you, and X to each of your non-flying
creatures. One branch per affordable X."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Earthquake(Card):
    card_name = "Earthquake"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("R", 1),))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    st.damage_opponent(xx)
                    st.note_crime()
                    st.damage_self(xx)  # you are a player too
                    for p in list(st.battlefield):
                        if p.is_creature_now and not st.has_keyword(p, "Flying"):
                            p.damage += xx
                    st.emit(f"Earthquake: {xx} to each non-flyer and each player")
                    st.check_deaths()
                    return None
                return fn

            acts.append(CardAction(f"cast Earthquake (X={x})", make(x)))
        return acts
