"""Steal Artifact — {2}{U}{U} Enchantment — Aura. Enchant artifact.
You control enchanted artifact.

Stealing control only matters against an opponent's artifact; you already control
your own, so this is inert. It still attaches (one branch per your artifact) and
counts as a cast enchantment."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class StealArtifact(Card):
    card_name = "Steal Artifact"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{2}{U}{U}",
                                    pred=lambda p: p.is_artifact)
