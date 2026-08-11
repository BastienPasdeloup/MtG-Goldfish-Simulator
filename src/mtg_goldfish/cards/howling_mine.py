"""Howling Mine — {2} Artifact.
At the beginning of each player's draw step, if this artifact is untapped, that
player draws an additional card.

Symmetric card draw — in a solitaire goldfish it fires on YOUR draw step (if
untapped), drawing you an extra card each turn."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class HowlingMine(Card):
    card_name = "Howling Mine"
    trigger_phase = Phase.DRAW

    def on_phase(self, state, perm, phase):
        p = state.find_permanent(perm.uid)
        if p is not None and not p.tapped:
            state.draw(1)
            state.emit("Howling Mine: draw an additional card")
        return None
