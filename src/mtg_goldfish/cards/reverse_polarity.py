"""Reverse Polarity — {W}{W} Instant.
You gain X life, where X is twice the damage dealt to you so far this turn by
artifacts.

Reads `state.artifact_damage_this_turn` (tallied by `damage_self(by_artifact=
True)`) and gains twice that."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ReversePolarity(Card):
    card_name = "Reverse Polarity"

    def on_resolve(self, state):
        x = 2 * state.artifact_damage_this_turn
        if x > 0:
            state.gain_life(x)
            state.emit(f"Reverse Polarity: gain {x} life ({state.life})")
        return None
