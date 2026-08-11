"""Mana Flare — {2}{R} Enchantment.
Whenever a player taps a land for mana, that player adds one mana of any type that
land produced.

Symmetric ramp — every land you tap yields one extra mana of the colour it
produced. Modelled as a per-land mana bonus in `available_mana_sources` (like
Gauntlet of Might's Mountain bonus, but for every land), so it feeds
affordability just like real doubled mana."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ManaFlare(Card):
    card_name = "Mana Flare"

    def land_mana_bonus(self, state, land):
        return 1
