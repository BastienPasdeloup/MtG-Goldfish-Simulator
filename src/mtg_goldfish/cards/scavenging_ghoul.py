"""Scavenging Ghoul — {3}{B} Creature — Zombie 2/2. Regenerate.
At the beginning of each end step, put a corpse counter on this creature for each
creature that died this turn.
Remove a corpse counter from this creature: Regenerate this creature.

Banks corpse counters each end step from the deaths-this-turn tracker; each corpse
counter can be spent to bank a regeneration shield."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ScavengingGhoul(Card):
    card_name = "Scavenging Ghoul"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        n = state.deaths_this_turn
        if n:
            p = state.find_permanent(perm.uid)
            if p is not None:
                p.counters["corpse"] = p.counters.get("corpse", 0) + n
                state.emit(f"Scavenging Ghoul: +{n} corpse counter(s)")
        return None

    def battlefield_actions(self, state, perm):
        if perm.counters.get("corpse", 0) <= 0 or perm.counters.get("regen_shield"):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.counters.get("corpse", 0) <= 0:
                return False
            p.counters["corpse"] -= 1
            return True

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["regen_shield"] = 1
                st.emit("Scavenging Ghoul: regeneration shield (removed a corpse counter)")
            return None

        return [CardAction.activated(
            "Scavenging Ghoul: remove a corpse counter — regenerate",
            pay, resolve, source_name="Scavenging Ghoul",
            ability_text="Regenerate")]
