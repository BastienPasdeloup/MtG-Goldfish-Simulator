"""Summer Bloom — {1}{G} Sorcery.
You may play up to three additional lands this turn."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SummerBloom(Card):
    card_name = "Summer Bloom"

    def on_resolve(self, state):
        state.bonus_land_drops += 3
        state.emit("Summer Bloom: +3 land plays this turn")
