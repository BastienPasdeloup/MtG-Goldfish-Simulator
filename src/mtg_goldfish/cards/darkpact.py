"""Darkpact — {B}{B}{B} Sorcery.
(Ante card.) You own target card in the ante. Exchange that card with the top
card of your library.

If a card is already in the ante, exchange it (it returns to the top of your
library; your top card is anted in its place). With nothing anted yet, it simply
antes your top card (a benign simplification consistent with the ante badge)."""
from __future__ import annotations

from ._common import ante_top_card
from .base import Card
from .registry import register


@register
class Darkpact(Card):
    card_name = "Darkpact"

    def on_resolve(self, state):
        target = next((c for c in state.exile if id(c) in state.ante_ids), None)
        if target is not None and state.library:
            old_top = state.library[0]
            state.exile.remove(target)
            state.ante_ids.discard(id(target))
            state.library[0] = target
            state.mark_known_in_library(target)
            state.exile.append(old_top)
            state.ante_ids.add(id(old_top))
            state.emit(f"Darkpact: exchange anted {target.name} for top card {old_top.name}")
        else:
            ante_top_card(state)
