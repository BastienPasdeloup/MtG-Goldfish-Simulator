"""Necromancy — {2}{B} Enchantment. Put a creature card from a graveyard onto
the battlefield under your control (becomes an Aura on it). The flash-speed /
cleanup-sacrifice clause is not modelled (treated as sorcery-speed reanimation)."""
from __future__ import annotations

from ._common import reanimation_aura_actions
from .base import Card
from .registry import register


@register
class Necromancy(Card):
    card_name = "Necromancy"

    def cast_actions(self, state):
        return reanimation_aura_actions(self, state)
