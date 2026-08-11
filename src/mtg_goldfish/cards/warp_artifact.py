"""Warp Artifact — {B}{B} Enchantment — Aura. Enchant artifact.
At the beginning of the upkeep of enchanted artifact's controller, this Aura deals
1 damage to that player.

Meant for an opponent's artifact; on one of your own it pings YOU 1 each upkeep
(via damage_self, black source) — a downside, but a real effect. One branch per
your artifact."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class WarpArtifact(Card):
    card_name = "Warp Artifact"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{B}{B}",
                                    pred=lambda p: p.is_artifact)

    def on_phase(self, state, perm, phase):
        dealt = state.damage_self(1, colors=("B",))
        state.emit(f"Warp Artifact: {dealt} damage to you")
        return None
