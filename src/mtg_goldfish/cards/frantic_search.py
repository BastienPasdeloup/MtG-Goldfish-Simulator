"""Frantic Search — {2}{U} Instant. Draw two cards, then discard two cards.
Untap up to three lands."""
from __future__ import annotations

from ._common import loot
from .base import Card
from .registry import register


def _untap_three_lands(st):
    n = 3
    for p in st.battlefield:
        if n <= 0:
            break
        if p.is_land and p.tapped:
            p.tapped = False
            n -= 1
    st.emit("Frantic Search: untap up to three lands")


@register
class FranticSearch(Card):
    card_name = "Frantic Search"

    def on_resolve(self, state):
        branches = loot(state, 2, 2, source="Frantic Search")
        if branches is None:
            _untap_three_lands(state)
            return None
        for b in branches:
            _untap_three_lands(b)
        return branches
