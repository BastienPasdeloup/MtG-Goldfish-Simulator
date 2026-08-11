"""Tangle Wire — {3} Artifact.
Fading 4 (enters with four fade counters; at your upkeep remove one, else
sacrifice it).
At the beginning of each player's upkeep, that player taps an untapped artifact,
creature, or land they control for each fade counter on Tangle Wire.

Symmetric stax: in a solitaire goldfish you tap N of your own permanents each of
your upkeeps (N = fade counters), then a fade counter is removed. A real downside
the search will weigh."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class TangleWire(Card):
    card_name = "Tangle Wire"
    trigger_phase = Phase.UPKEEP

    def enters_with_counters(self, state):
        return {"fade": 4}  # Fading 4

    def on_phase(self, state, perm, phase):
        n = perm.counters.get("fade", 0)
        # Tap n untapped artifacts / creatures / lands you control.
        tappable = [p for p in state.battlefield
                    if not p.tapped and (p.is_artifact or p.is_creature_now or p.is_land)]
        for p in tappable[:n]:
            p.tapped = True
        if tappable[:n]:
            state.emit(f"Tangle Wire: tap {min(n, len(tappable))} of your permanents")
        # Fading: remove a fade counter, or sacrifice it if there are none.
        if perm.counters.get("fade", 0) > 0:
            perm.counters["fade"] -= 1
        else:
            state.emit("Tangle Wire: no fade counters left — sacrifice")
            state.leaves_battlefield(perm, "graveyard")
        return None
