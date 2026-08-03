"""Exhume — {1}{B} Sorcery. Each player puts a creature card from their graveyard
onto the battlefield. Against a phantom opponent, only you reanimate (branch over
each creature card in your graveyard)."""
from __future__ import annotations

from ._common import reanimate_branches
from .base import Card
from .registry import register


@register
class Exhume(Card):
    card_name = "Exhume"

    def on_resolve(self, state):
        return reanimate_branches(state)
