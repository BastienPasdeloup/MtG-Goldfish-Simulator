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

    def equip_mod(self, state, perm):
        # "Enchanted creature gets -1/-0" for as long as Animate Dead is attached
        # (applied to the host's effective power via the attachment).
        return (-1, 0)

    def is_castable(self, state):
        # An Aura can't be cast with no legal target — a reanimation Aura needs a
        # creature card in a graveyard (also gates the graveyard-recast path).
        return any(c.is_creature for c in state.graveyard)

    def cast_actions(self, state):
        return reanimation_aura_actions(self, state)
