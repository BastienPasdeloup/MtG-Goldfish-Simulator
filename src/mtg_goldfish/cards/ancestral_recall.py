"""Ancestral Recall — {U} Instant.
Target player draws three cards. (Targeting yourself — the only player — draw 3.)"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AncestralRecall(Card):
    card_name = "Ancestral Recall"

    def on_resolve(self, state):
        state.emit("Ancestral Recall: draw three cards")
        state.draw(3)
