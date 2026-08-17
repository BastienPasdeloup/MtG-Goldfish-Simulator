"""Hurkyl's Recall — {1}{U} Instant.
Return all artifacts target player owns to their hand.

Targets you (the phantom opponent owns nothing): returns every artifact you
control to your hand — artifact tokens cease to exist. Useful for re-buying
enters-the-battlefield artifacts."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HurkylsRecall(Card):
    card_name = "Hurkyl's Recall"

    def on_resolve(self, state):
        for p in [p for p in list(state.battlefield) if p.is_artifact]:
            live = state.find_permanent(p.uid)
            if live is not None:
                state.emit(f"Hurkyl's Recall: return {live.name} to hand")
                state.leaves_battlefield(live, "hand", reason=None)
