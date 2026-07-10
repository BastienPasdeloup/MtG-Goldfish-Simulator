"""Emrakul, the Promised End — {13} Legendary Creature — Eldrazi 13/13.
Costs {1} less per card type among cards in your graveyard. Flying, trample,
protection from instants. The mind-control-a-turn cast trigger is
opponent-facing (no-op in a goldfish); it enters as a 13/13 body."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card
from .registry import register

_TYPES = ("creature", "land", "artifact", "enchantment", "instant",
          "sorcery", "planeswalker", "battle", "kindred", "tribal")


@register
class EmrakulThePromisedEnd(Card):
    card_name = "Emrakul, the Promised End"

    def cast_cost(self, state):
        types = set()
        for c in state.graveyard:
            tl = c.type_line.lower()
            for t in _TYPES:
                if t in tl:
                    types.add(t)
        reduction = len(types)
        return ManaCost(generic=max(0, 13 - reduction))
