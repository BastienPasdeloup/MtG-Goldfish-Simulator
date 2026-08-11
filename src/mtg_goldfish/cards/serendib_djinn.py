"""Serendib Djinn — {2}{U}{U} Creature — Djinn 5/6. Flying.
At the beginning of your upkeep, sacrifice a land. If you sacrifice an Island this
way, this creature deals 3 damage to you.
When you control no lands, sacrifice this creature.

A big flyer that eats a land each upkeep — a non-Island if you have one (else an
Island, which pings you 3). With no lands it sacrifices itself."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class SerendibDjinn(Card):
    card_name = "Serendib Djinn"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        lands = [p for p in state.battlefield if p.is_land]
        if not lands:
            me = state.find_permanent(perm.uid)
            if me is not None:
                state.emit("Serendib Djinn: no lands — sacrifice")
                state.leaves_battlefield(me, "graveyard", reason="sacrifice")
            return None
        # Prefer sacrificing a non-Island (avoids the 3 damage).
        non_islands = [p for p in lands if "island" not in p.type_line.lower()]
        victim = (non_islands or lands)[0]
        is_island = "island" in victim.type_line.lower()
        state.emit(f"Serendib Djinn: sacrifice {victim.name}")
        state.leaves_battlefield(victim, "graveyard", reason="sacrifice")
        if is_island:
            dealt = state.damage_self(3, colors=("U",))
            state.emit(f"Serendib Djinn: sacrificed an Island — {dealt} damage to you")
        return None
