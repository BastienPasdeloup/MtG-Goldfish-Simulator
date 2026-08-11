"""Wanderlust — {2}{G} Enchantment — Aura. Enchant creature.
At the beginning of the upkeep of enchanted creature's controller, this Aura deals
1 damage to that player.

Enchant one of your creatures; each of your upkeeps it pings you 1 (via
damage_self, green source) — a downside, but a real effect."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Wanderlust(Card):
    card_name = "Wanderlust"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{2}{G}")

    def on_phase(self, state, perm, phase):
        dealt = state.damage_self(1, colors=("G",))
        state.emit(f"Wanderlust: {dealt} damage to you")
        return None
