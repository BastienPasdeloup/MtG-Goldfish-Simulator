"""Reverse Damage — {1}{W}{W} Instant.
The next time a source of your choice would deal damage to you this turn, prevent
that damage. You gain life equal to the damage prevented this way.

Adds a one-shot lifegain prevention shield: the next damage instance dealt to you
is prevented in full and you gain that much life."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ReverseDamage(Card):
    card_name = "Reverse Damage"

    def on_resolve(self, state):
        state.prevent_shields.append((10 ** 6, None, True))
        state.emit("Reverse Damage: next damage to you is prevented and gained as life")
