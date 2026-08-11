"""Disintegrate — {X}{R} Sorcery.
Deals X damage to any target. (If a creature, it can't be regenerated and is
exiled if it dies — regeneration/where-it-dies are irrelevant in a goldfish.)

One branch per (affordable X) × (target: the opponent, or one of your creatures)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class Disintegrate(Card):
    card_name = "Disintegrate"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("R", 1),))
            if not can_afford(state, cost):
                continue
            for label, apply in damage_any_target_options(state):
                def make(xx, c, ap):
                    def fn(st):
                        card = next((k for k in st.hand if k.name == self.card_name), None)
                        if card is None or not begin_cast(st, card, c):
                            return None
                        resolve_to_graveyard(st, card)
                        st.emit(f"Disintegrate: {xx} damage")
                        ap(st, xx)
                        return None
                    return fn
                acts.append(CardAction(f"cast Disintegrate (X={x}) → {label}",
                                       make(x, cost, apply)))
        return acts
