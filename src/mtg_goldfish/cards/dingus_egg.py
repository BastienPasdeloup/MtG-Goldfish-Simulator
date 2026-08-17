"""Dingus Egg — {4} Artifact.
Whenever a land is put into a graveyard from the battlefield, this artifact deals
2 damage to that land's controller.

Symmetric in a goldfish: whenever one of YOUR lands dies (to a graveyard) it
deals 2 to you — a downside that pairs with your own land-sacrifice/destruction."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DingusEgg(Card):
    card_name = "Dingus Egg"

    def on_other_leave(self, state, perm, left, to, reason):
        if left.is_land and to == "graveyard":
            state.emit(f"Dingus Egg: {left.name} died — deals 2 damage to you")
            state.damage_self(2, by_artifact=True)
