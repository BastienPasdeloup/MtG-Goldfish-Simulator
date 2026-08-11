"""Sea Serpent — {5}{U} Creature — Serpent 5/5.
This creature can't attack unless defending player controls an Island.
When you control no Islands, sacrifice this creature.

The attack restriction depends on the opponent's Islands (never any → it can't
attack). The "sacrifice if you control no Islands" clause is checked at your
upkeep (approximating the state trigger)."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class SeaSerpent(Card):
    card_name = "Sea Serpent"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        if not any(p.is_land and "island" in p.type_line.lower() for p in state.battlefield):
            p = state.find_permanent(perm.uid)
            if p is not None:
                state.emit("Sea Serpent: no Island — sacrifice")
                state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
