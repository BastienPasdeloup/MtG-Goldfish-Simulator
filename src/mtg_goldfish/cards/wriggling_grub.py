"""Wriggling Grub — {1}{B} Creature 1/1. When it dies, create two 1/1 black and
green Worm creature tokens."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WrigglingGrub(Card):
    card_name = "Wriggling Grub"

    def on_leave(self, state, permanent):
        for _ in range(2):
            state.make_token("Worm", 1, 1, "Creature — Worm")
        state.emit("Wriggling Grub: create two 1/1 Worms")
