"""Gamble — {R} Sorcery. Search your library for a card, put it into your hand,
discard a card at random, then shuffle. (The random discard is resolved with a
seeded RNG, deterministic per search branch.)"""
from __future__ import annotations

import random

from ._common import branch_over
from .base import Card
from .registry import register


@register
class Gamble(Card):
    card_name = "Gamble"

    def on_resolve(self, state):
        candidates = state.search_library(lambda c: True)
        if not candidates:
            return None

        def fn(st, name):
            card = next(c for c in st.library if c.name == name)
            st.take_from_library(card)
            st.hand.append(card)
            st.shuffle_library()
            if st.hand:
                rng = random.Random(st.rng_seed * 7919 + st._next_uid)
                st._next_uid += 1
                victim = st.hand[rng.randrange(len(st.hand))]
                st.emit(f"Gamble: found {name}, discard {victim.name} at random")
                st.discard(victim)
            return None

        return branch_over(state, [c.name for c in candidates], fn)
