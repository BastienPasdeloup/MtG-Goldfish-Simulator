"""Starting Town — Land — Town. Enters tapped unless it's your first, second,
or third turn. {T}: Add {C}. {T}, Pay 1 life: Add one mana of any color."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class StartingTown(Card):
    card_name = "Starting Town"

    def etb_tapped(self, state):
        return state.turn > 3

    def mana_abilities(self, state):
        return [
            ManaAbility(amount=1, choices=("C",)),
            ManaAbility(amount=1, choices=("W", "U", "B", "R", "G"), life_cost=1),
        ]
