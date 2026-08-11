"""Demonic Attorney — {1}{B}{B} Sorcery.
(Ante card.) Each player antes the top card of their library.

You ante the top card of your library (exiled with an "ante" badge); the phantom
opponent's ante has no goldfish effect."""
from __future__ import annotations

from ._common import ante_top_card
from .base import Card
from .registry import register


@register
class DemonicAttorney(Card):
    card_name = "Demonic Attorney"

    def on_resolve(self, state):
        ante_top_card(state)
        state.emit("Demonic Attorney: each player antes the top of their library")
