"""Dark Ritual — {B} Instant.
Add {B}{B}{B}. (A ritual: net +2 black mana into your pool.)"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DarkRitual(Card):
    card_name = "Dark Ritual"

    def on_resolve(self, state):
        state.mana_pool.add("B", 3)
        state.emit("Dark Ritual: add {B}{B}{B}")
