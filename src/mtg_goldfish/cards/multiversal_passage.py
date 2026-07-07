"""Multiversal Passage — Land.

Land with no fixed colours resolved from Scryfall; approximated as tapping for
one mana of any colour in the commander's colour identity.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MultiversalPassage(Card):
    card_name = 'Multiversal Passage'

    def mana_abilities(self, state) -> list[ManaAbility]:
        identity = tuple(state.commander_color_identity) or ("W", "U", "B", "R", "G")
        return [ManaAbility(amount=1, choices=identity)]
