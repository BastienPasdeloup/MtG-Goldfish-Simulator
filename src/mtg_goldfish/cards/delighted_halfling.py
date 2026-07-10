"""Delighted Halfling — {G} Creature — Halfling Citizen 1/2.
{T}: Add {C}. {T}: Add one mana of any color for a legendary spell.
Approximation: the second ability is modelled as an unrestricted
identity-color source — this deck's key spells (Lumra, Six, Nissa, Emrakul,
Ugin, Tezzeret...) are mostly legendary, and 'can't be countered' is
meaningless in a goldfish."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class DelightedHalfling(Card):
    card_name = "Delighted Halfling"

    def mana_abilities(self, state):
        return [
            ManaAbility(amount=1, choices=any_identity_color(state)),
            ManaAbility(amount=1, choices=("C",)),
        ]
