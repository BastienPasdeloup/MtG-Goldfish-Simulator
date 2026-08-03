"""Tainted Indulgence — {U}{B} Instant. Draw two cards. Then discard a card
unless there are five or more mana values among cards in your graveyard."""
from __future__ import annotations

from ._common import discard_branches, mv
from .base import Card
from .registry import register


@register
class TaintedIndulgence(Card):
    card_name = "Tainted Indulgence"

    def on_resolve(self, state):
        state.draw(2)
        state.emit(f"Tainted Indulgence: draw two ({len(state.hand)} in hand)")
        if len({mv(c) for c in state.graveyard}) >= 5:
            state.emit("Tainted Indulgence: 5+ mana values in graveyard — no discard")
            return None
        return discard_branches(state, 1, source="Tainted Indulgence")
