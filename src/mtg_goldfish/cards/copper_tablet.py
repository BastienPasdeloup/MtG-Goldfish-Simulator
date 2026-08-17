"""Copper Tablet — {2} Artifact.
At the beginning of each player's upkeep, this artifact deals 1 damage to that
player. In a solitaire goldfish that is you, each of your upkeeps — a downside."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class CopperTablet(Card):
    card_name = "Copper Tablet"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        state.emit("Copper Tablet: deals 1 damage to you")
        state.damage_self(1, by_artifact=True)
        return None
