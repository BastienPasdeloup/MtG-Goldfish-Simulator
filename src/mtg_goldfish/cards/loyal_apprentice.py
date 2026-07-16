"""Loyal Apprentice — {1}{R} Creature 2/1, haste.
Lieutenant — At the beginning of combat on your turn, if you control your
commander, create a 1/1 colorless Thopter artifact creature token with flying
that gains haste until end of turn."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class LoyalApprentice(Card):
    card_name = "Loyal Apprentice"
    trigger_phase = Phase.BEGIN_COMBAT

    def on_phase(self, state, perm, phase):
        if not state.commander_in_play():
            return
        tok = state.make_token("Thopter", 1, 1, "Artifact Creature — Thopter",
                               text="Flying")
        tok.temp_keywords.add("haste")
        state.emit("Loyal Apprentice: create a 1/1 flying Thopter (haste)")
