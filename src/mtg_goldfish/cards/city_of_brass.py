"""City of Brass — Land. Taps for any colour; deals 1 damage to you when tapped."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class CityOfBrass(Card):
    card_name = 'City of Brass'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U', 'B', 'R', 'G'))]

    def on_tap_for_mana(self, state, permanent, color) -> None:
        # "Whenever City of Brass becomes tapped, it deals 1 damage to you."
        state.life -= 1
