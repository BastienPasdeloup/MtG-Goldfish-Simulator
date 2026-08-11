"""Fireball — {X}{R} Sorcery.
Costs {1} more per target beyond the first; deals X damage divided among any
number of targets.

The goldfish line is all X to the opponent (a single target — no extra cost); the
multi-target split isn't modelled (splitting X across your own creatures + the
opponent is strictly worse). One branch per affordable X."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Fireball(Card):
    card_name = "Fireball"

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
                    dealt = st.damage_opponent(xx)
                    st.note_crime()
                    st.emit(f"Fireball: {dealt} damage to opponent")
                    return None
                return fn

            acts.append(CardAction(f"cast Fireball (X={x}) → opponent", make(x)))
        return acts
