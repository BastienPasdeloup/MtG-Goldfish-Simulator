"""Sink into Stupor // Soporific Springs — MDFC.
Front (instant): "Return target spell or nonland permanent an opponent
controls" — never castable in solitaire (no opponent).
Back (land): enters tapped unless you pay 3 life; {T}: Add {U}.
The engine plays it as the land face (branch: pay 3 / tapped)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class SinkIntoStupor(Card):
    card_name = "Sink into Stupor // Soporific Springs"
    enters_transformed = True  # on the battlefield it is Soporific Springs

    def is_castable(self, state):
        return False  # front face targets an opponent's spell/permanent

    def etb_modes(self, state):
        modes = []
        if state.life > 3:
            modes.append({"label": "pay 3 life, untapped", "tapped": False, "life": 3})
        modes.append({"label": "tapped", "tapped": True, "life": 0})
        return modes

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]
