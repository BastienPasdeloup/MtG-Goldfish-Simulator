"""Armageddon Clock — {6} Artifact.
At the beginning of your upkeep, put a doom counter on it.
At the beginning of your draw step, it deals damage equal to its doom counters to
each player.
{4}: Remove a doom counter from it. Any player may activate this only during any
upkeep step.

Accumulates doom counters each upkeep and pings YOU for that many each draw step
(the phantom opponent is unaffected). The {4} de-tick is offered during your
upkeep."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ArmageddonClock(Card):
    card_name = "Armageddon Clock"

    def phase_stack_items(self, state, perm, phase):
        if phase not in (Phase.UPKEEP, Phase.DRAW):
            return []
        return super().phase_stack_items(state, perm, phase)

    def on_phase(self, state, perm, phase):
        p = state.find_permanent(perm.uid)
        if p is None:
            return None
        if phase == Phase.UPKEEP:
            p.counters["doom"] = p.counters.get("doom", 0) + 1
            state.emit(f"Armageddon Clock: put a doom counter ({p.counters['doom']})")
        elif phase == Phase.DRAW:
            n = p.counters.get("doom", 0)
            if n > 0:
                dealt = state.damage_self(n, by_artifact=True)
                state.emit(f"Armageddon Clock: {dealt} damage to you ({state.life})")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if state.phase != Phase.UPKEEP or perm.counters.get("doom", 0) <= 0:
            return []
        cost = ManaCost(generic=4)
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None and p.counters.get("doom", 0) > 0:
                p.counters["doom"] -= 1
                st.emit(f"Armageddon Clock: remove a doom counter ({p.counters['doom']})")
            return None

        return [CardAction.activated(
            "Armageddon Clock: {4} — remove a doom counter",
            pay, resolve, source_name="Armageddon Clock",
            ability_text="Remove a doom counter")]
