"""Fastbond — {G} Enchantment.
You may play any number of lands on each of your turns.
Whenever you play a land, if it wasn't the first land you played this turn, this
enchantment deals 1 damage to you.

Grants unlimited extra land drops; each extra land (2nd, 3rd, ...) pings you for 1
(via damage_self, so prevention can apply)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Fastbond(Card):
    card_name = "Fastbond"

    def extra_land_drops(self, state, perm):
        return 99  # "any number of lands"

    def on_other_etb(self, state, perm, entering):
        # Only lands actually PLAYED (not fetched) beyond the first this turn ping you.
        if (entering.is_land and entering.turn_flags.get("played_as_land")
                and state.lands_played_this_turn > 1):
            state.emit("Fastbond: 1 damage to you (extra land)")
            state.damage_self(1)
