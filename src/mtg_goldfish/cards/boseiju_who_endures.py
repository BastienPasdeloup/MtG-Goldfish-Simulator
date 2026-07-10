"""Boseiju, Who Endures — Legendary Land.
{T}: Add {G}. The channel ability targets an opponent's permanent, so it has
no use in a solitaire game — fully modelled as a Forest-like legendary land."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class BoseijuWhoEndures(Card):
    card_name = "Boseiju, Who Endures"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
