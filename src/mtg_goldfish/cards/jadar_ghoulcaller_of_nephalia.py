"""Jadar, Ghoulcaller of Nephalia — {1}{B} Legendary Creature 1/1.
At the beginning of your end step, if you control no creatures with decayed,
create a 2/2 black Zombie creature token with decayed."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class JadarGhoulcallerOfNephalia(Card):
    card_name = "Jadar, Ghoulcaller of Nephalia"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        if any(p.counters.get("decayed") for p in state.battlefield):
            return
        tok = state.make_token(
            "Zombie", 2, 2, "Creature — Zombie",
            text="Decayed (can't block; when it attacks, sacrifice it at end of combat).")
        tok.counters["decayed"] = 1
        state.emit("Jadar: create a 2/2 decayed Zombie")
