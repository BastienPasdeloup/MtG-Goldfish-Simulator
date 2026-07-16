"""Gravecrawler — {B} Creature 2/1, can't block.
You may cast this card from your graveyard as long as you control a Zombie."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


def _controls_zombie(state) -> bool:
    return any("zombie" in p.type_line.lower() for p in state.battlefield)


@register
class Gravecrawler(Card):
    card_name = "Gravecrawler"

    def graveyard_actions(self, state):
        from ..engine.actions import (begin_cast, can_afford,
                                      resolve_to_battlefield)

        cost = self.cast_cost(state)
        if not _controls_zombie(state) or not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None or not _controls_zombie(st):
                return None
            if not begin_cast(st, card, cost, zone=st.graveyard, tag="from graveyard"):
                return None
            return resolve_to_battlefield(st, card) or None

        return [CardAction("cast Gravecrawler from graveyard", fn)]
