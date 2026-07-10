"""Urza's Tower — Land — Urza's Tower.
{T}: Add {C}; {C}{C}{C} if you control an Urza's Mine and an Urza's
Power-Plant. In this deck only Planar Nexus ("every nonbasic land type") can
satisfy that, so the check looks for it by name (one Nexus can't be both at
once in real rules — two would be needed — but singleton Commander makes the
distinction moot: we require one Nexus, a documented approximation)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class UrzasTower(Card):
    card_name = "Urza's Tower"

    def mana_abilities(self, state):
        nexus = any(p.name == "Planar Nexus" for p in state.battlefield)
        return [ManaAbility(amount=3 if nexus else 1, choices=("C",))]
