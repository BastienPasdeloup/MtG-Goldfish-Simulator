"""Mightstone — {4} Artifact. Attacking creatures get +1/+0.

A continuous static (`static_pt_bonus`) applied to every attacking creature
(both players', but only yours exist in a goldfish)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Mightstone(Card):
    card_name = "Mightstone"

    def static_pt_bonus(self, state, source, perm):
        return (1, 0) if perm.uid in state.attackers else (0, 0)
