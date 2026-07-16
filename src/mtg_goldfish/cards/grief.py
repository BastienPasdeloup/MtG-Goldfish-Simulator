"""Grief — {2}{B}{B} Creature 3/2, menace. Evoke—exile a black card.
When it enters, target opponent reveals their hand and discards a nonland card.
Against a phantom opponent that ETB does nothing; Grief's role in a goldfish is
its body plus the evoke line (a free creature that enters and is sacrificed,
feeding death triggers)."""
from __future__ import annotations

from ._common import evoke_actions
from .base import Card
from .registry import register


@register
class Grief(Card):
    card_name = "Grief"

    def hand_actions(self, state):
        return evoke_actions(self, state, "B")

    def on_etb(self, state, permanent):
        state.emit("Grief: opponent has no revealable hand in a goldfish")
