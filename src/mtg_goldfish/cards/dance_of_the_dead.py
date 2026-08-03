"""Dance of the Dead — {1}{B} Enchantment — Aura. Put an enchanted creature card
from a graveyard onto the battlefield TAPPED under your control. The +1/+1,
doesn't-untap, and pay-{1}{B}-to-untap clauses are not modelled."""
from __future__ import annotations

from ._common import reanimation_aura_actions
from .base import Card
from .registry import register


@register
class DanceOfTheDead(Card):
    card_name = "Dance of the Dead"

    def cast_actions(self, state):
        return reanimation_aura_actions(self, state, tapped=True)
