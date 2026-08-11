"""Manabarbs — {3}{R} Enchantment.
Whenever a player taps a land for mana, this enchantment deals 1 damage to that
player.

Symmetric — every time YOU tap a land for mana it pings you 1 (via damage_self,
red source). Punishes a long game / heavy mana use. Fired by the land-tap
broadcast in pay_cost."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Manabarbs(Card):
    card_name = "Manabarbs"

    def on_land_tapped_for_mana(self, state, perm, land, color):
        state.damage_self(1, colors=("R",))
        state.emit("Manabarbs: 1 damage to you (tapped a land)")
        return None
