"""Shallow Grave — {1}{B} Instant. Return the top creature card of your graveyard
to the battlefield with haste; exile it at the beginning of the next end step."""
from __future__ import annotations

from ._common import reanimate_top_creature
from .base import Card
from .registry import register


@register
class ShallowGrave(Card):
    card_name = "Shallow Grave"

    def is_castable(self, state):
        return any(c.is_creature for c in state.graveyard)

    def on_resolve(self, state):
        return reanimate_top_creature(state, note=" (haste; exile at end step)")
