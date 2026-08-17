"""Weakstone — {4} Artifact. Attacking creatures get -1/-0.

A continuous static (`static_pt_bonus`) applied to every attacking creature
(symmetric — it also weakens your own attackers)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Weakstone(Card):
    card_name = "Weakstone"

    def static_pt_bonus(self, state, source, perm):
        return (-1, 0) if perm.uid in state.attackers else (0, 0)
