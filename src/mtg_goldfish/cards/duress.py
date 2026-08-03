"""Duress — {B} Sorcery. Target opponent reveals their hand; you choose a
noncreature, nonland card; that player discards it. Against a phantom opponent
this does nothing (they reveal no hand); it can only be cast for value it lacks
here, so it is chiefly a cheap spell to bin (e.g. via other discard outlets)."""
from __future__ import annotations

from ._common import discard_spell_actions
from .base import Card
from .registry import register


@register
class Duress(Card):
    card_name = "Duress"

    def cast_actions(self, state):
        # "Target opponent" — cannot be aimed at yourself.
        return discard_spell_actions(self, state, pred=lambda c: False,
                                     can_target_self=False)
