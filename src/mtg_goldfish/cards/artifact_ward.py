"""Artifact Ward — {W} Enchantment — Aura. Enchant creature.
Enchanted creature can't be blocked by artifact creatures, prevents all damage
from artifact sources, and can't be targeted by abilities from artifact sources.

All three clauses concern artifact sources/blockers, which don't act against your
creatures in a goldfish — so the Aura is functionally inert. It still enters
attached to one of your creatures (one branch per host)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class ArtifactWard(Card):
    card_name = "Artifact Ward"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost=self.cast_cost(state))
