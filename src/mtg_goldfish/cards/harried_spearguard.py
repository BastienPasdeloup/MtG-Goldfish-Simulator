"""Harried Spearguard — {R} Creature 1/1, haste. When it dies, create a 1/1
black Rat creature token that can't block."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HarriedSpearguard(Card):
    card_name = "Harried Spearguard"

    def on_leave(self, state, permanent):
        state.make_token("Rat", 1, 1, "Creature — Rat", text="This token can't block.")
        state.emit("Harried Spearguard: create a 1/1 Rat")
