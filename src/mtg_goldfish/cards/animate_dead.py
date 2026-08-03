"""Animate Dead — {1}{B} Enchantment — Aura. Reanimate a creature card from a
graveyard (Aura attaches to it; the -1/-0 and sacrifice-on-leave are not
modelled)."""
from __future__ import annotations

from ._common import reanimation_aura_actions
from .base import Card
from .registry import register


@register
class AnimateDead(Card):
    card_name = "Animate Dead"

    def cast_actions(self, state):
        return reanimation_aura_actions(self, state)
