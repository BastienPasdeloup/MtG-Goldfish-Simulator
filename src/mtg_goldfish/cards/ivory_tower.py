"""Ivory Tower — {1} Artifact.
At the beginning of your upkeep, you gain X life, where X is the number of cards
in your hand minus 4."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class IvoryTower(Card):
    card_name = "Ivory Tower"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        x = len(state.hand) - 4
        if x > 0:
            state.gain_life(x)
            state.emit(f"Ivory Tower: gain {x} life ({state.life})")
        return None
