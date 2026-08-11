"""Time Walk — {1}{U} Sorcery. Take an extra turn after this one.

Queues an extra turn (state.extra_turns) — a full untap/draw/main/combat cycle
that does not advance the turn counter."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TimeWalk(Card):
    card_name = "Time Walk"

    def on_resolve(self, state):
        state.extra_turns += 1
        state.emit("Time Walk: take an extra turn")
