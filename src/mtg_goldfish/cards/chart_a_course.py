"""Chart a Course — {1}{U} Sorcery. Draw two cards. Then discard a card unless
you attacked this turn."""
from __future__ import annotations

from ._common import discard_branches
from .base import Card
from .registry import register


@register
class ChartACourse(Card):
    card_name = "Chart a Course"

    def on_resolve(self, state):
        state.draw(2)
        state.emit(f"Chart a Course: draw two ({len(state.hand)} in hand)")
        if state.attacked_this_turn:
            state.emit("Chart a Course: attacked this turn — no discard")
            return None
        return discard_branches(state, 1, source="Chart a Course")
