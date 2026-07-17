"""Ancient Cornucopia — {2}{G} Artifact. {T}: Add one mana of any color.
Whenever you cast a spell that's one or more colors, you may gain 1 life for each
of that spell's colors (only once each turn)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class AncientCornucopia(Card):
    card_name = "Ancient Cornucopia"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]

    def on_cast_other(self, state, perm, card):
        if perm.turn_flags.get("cornucopia"):
            return
        colors = len(card.colors)
        if colors > 0:
            perm.turn_flags["cornucopia"] = 1
            state.life += colors
            state.emit(f"Ancient Cornucopia: gain {colors} life ({state.life})")
