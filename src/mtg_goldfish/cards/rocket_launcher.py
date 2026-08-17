"""Rocket Launcher — {4} Artifact.
{2}: This artifact deals 1 damage to any target. Destroy this artifact at the
beginning of the next end step. Activate only if you've controlled this artifact
continuously since the beginning of your most recent turn.

The continuity clause is treated as satisfied (a permanent you control has been on
the battlefield). Each activation pings 1 (one branch per target) and arms the
artifact to be destroyed at the next end step, so it can fire repeatedly until
then."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class RocketLauncher(Card):
    card_name = "Rocket Launcher"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        if perm.counters.get("armed"):
            state.emit("Rocket Launcher: destroyed (end step)")
            state.leaves_battlefield(perm, "graveyard", reason=None)
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    if not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    p = st.find_permanent(perm.uid)
                    if p is not None:
                        p.counters["armed"] = 1  # destroyed at next end step
                    return True

                def resolve(st):
                    apply(st, 1)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Rocket Launcher: {{2}} → 1 damage to {suffix}",
                pay, resolve, source_name="Rocket Launcher",
                ability_text="Deal 1 damage to any target"))
        return acts
