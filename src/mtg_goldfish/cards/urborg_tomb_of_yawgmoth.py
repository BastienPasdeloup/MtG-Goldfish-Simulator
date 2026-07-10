"""Urborg, Tomb of Yawgmoth — Legendary Land.
"Each land is a Swamp" makes Urborg itself tap for {B}; the global Swamp-ness
of other lands is not modelled (black mana has no use in a green-identity
Commander goldfish beyond generic costs, which lands already cover)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class UrborgTombOfYawgmoth(Card):
    card_name = "Urborg, Tomb of Yawgmoth"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]
