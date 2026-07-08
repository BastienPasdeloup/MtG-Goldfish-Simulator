"""Mana Confluence — Land. Taps for any colour; costs 1 life per activation."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class ManaConfluence(Card):
    card_name = 'Mana Confluence'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U', 'B', 'R', 'G'))]

    def on_tap_for_mana(self, state, permanent, color) -> None:
        # "{T}, Pay 1 life: Add one mana of any color."
        state.life -= 1
