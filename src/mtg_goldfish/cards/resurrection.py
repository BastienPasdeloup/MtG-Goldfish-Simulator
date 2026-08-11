"""Resurrection — {2}{W}{W} Sorcery.
Return target creature card from your graveyard to the battlefield.

Reanimation: one branch per distinct creature card in your graveyard (it enters
untapped and its ETB fires)."""
from __future__ import annotations

from ._common import reanimate_branches
from .base import Card
from .registry import register


@register
class Resurrection(Card):
    card_name = "Resurrection"

    def on_resolve(self, state):
        return reanimate_branches(state, note=" (Resurrection)")
