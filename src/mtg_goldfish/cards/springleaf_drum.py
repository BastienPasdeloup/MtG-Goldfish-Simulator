"""Springleaf Drum — {1} Artifact. {T}, Tap an untapped creature you control:
Add one mana of any color. The creature-tap cost is applied via on_tap_for_mana
(an untapped creature is tapped when the Drum makes mana)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class SpringleafDrum(Card):
    card_name = "Springleaf Drum"

    def mana_abilities_perm(self, state, perm):
        if any(p.is_creature_now and not p.tapped for p in state.battlefield):
            return [ManaAbility(amount=1, choices=any_identity_color(state))]
        return []

    def on_tap_for_mana(self, state, permanent, color):
        creature = next((p for p in state.battlefield
                         if p.is_creature_now and not p.tapped), None)
        if creature is not None:
            creature.tapped = True
            state.emit(f"Springleaf Drum: tap {creature.name} for mana")
