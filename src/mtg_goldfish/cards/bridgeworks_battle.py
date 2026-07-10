"""Bridgeworks Battle // Tanglespan Bridgeworks — Sorcery // Land (MDFC).
Played as the land back face: pay 3 life to enter untapped, else tapped;
{T}: Add {G}. The front sorcery (a fight spell) has no meaningful use in a
solitaire game and is not castable — documented approximation."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class BridgeworksBattle(Card):
    card_name = "Bridgeworks Battle // Tanglespan Bridgeworks"
    enters_transformed = True  # on the battlefield it is Tanglespan Bridgeworks

    def is_castable(self, state):
        return False  # front face: fight — no opponent creatures to fight

    def etb_modes(self, state):
        modes = []
        if state.life > 3:
            modes.append({"label": "pay 3 life, untapped", "tapped": False, "life": 3})
        modes.append({"label": "tapped", "tapped": True, "life": 0})
        return modes

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
