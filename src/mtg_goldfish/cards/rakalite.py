"""Rakalite — {6} Artifact.
{2}: Prevent the next 1 damage that would be dealt to any target this turn.
Return this artifact to its owner's hand at the beginning of the next end step.

A repeatable {2}-per-1 prevention shield (against your self-damage) that bounces
itself back to hand at the next end step once used, so it can be recast."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class Rakalite(Card):
    card_name = "Rakalite"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        if perm.counters.get("armed"):
            state.emit("Rakalite: return to hand (end step)")
            state.leaves_battlefield(perm, "hand", reason=None)
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            if not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["armed"] = 1
            return True

        def resolve(st):
            st.prevent_shields.append((1, None))
            st.emit("Rakalite: prevent the next 1 damage to you this turn")
            return None

        return [CardAction.activated(
            "Rakalite: {2} — prevent the next 1 damage",
            pay, resolve, source_name="Rakalite",
            ability_text="Prevent the next 1 damage this turn")]
