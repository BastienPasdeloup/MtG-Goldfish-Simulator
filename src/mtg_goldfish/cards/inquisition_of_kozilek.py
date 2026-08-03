"""Inquisition of Kozilek — {B} Sorcery. Target player reveals their hand; you
choose a nonland card with mana value 3 or less; that player discards it.
"Target player" lets you aim it at YOURSELF to bin a cheap nonland (a graveyard
enabler); against the phantom opponent it does nothing."""
from __future__ import annotations

from ._common import discard_spell_actions, mv
from .base import Card
from .registry import register


@register
class InquisitionOfKozilek(Card):
    card_name = "Inquisition of Kozilek"

    def cast_actions(self, state):
        return discard_spell_actions(
            self, state, pred=lambda c: not c.is_land and mv(c) <= 3)
