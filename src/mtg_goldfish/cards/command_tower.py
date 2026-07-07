"""Command Tower — land, taps for one mana of any colour in your commander's
colour identity."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class CommandTower(Card):
    card_name = "Command Tower"

    def mana_abilities(self, state) -> list[ManaAbility]:
        identity = tuple(state.commander_color_identity) or ("C",)
        return [ManaAbility(amount=1, choices=identity)]
