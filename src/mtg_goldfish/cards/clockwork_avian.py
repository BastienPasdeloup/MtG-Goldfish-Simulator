"""Clockwork Avian — {5} Artifact Creature — Bird 0/4, Flying.
Enters with four +1/+0 counters (a 4/4 flier). At end of combat, if it attacked
or blocked this combat, remove a +1/+0 counter. {X}, {T}: put up to X +1/+0
counters on it (max four total); activate only during your upkeep.

Same mechanic as Clockwork Beast (four counters instead of seven)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ClockworkAvian(Card):
    card_name = "Clockwork Avian"
    trigger_phase = Phase.END_COMBAT

    def enters_with_counters(self, state):
        return {"+1/+0": 4}

    def on_phase(self, state, perm, phase):
        if perm.turn_flags.get("attacked") and perm.counters.get("+1/+0", 0) > 0:
            perm.counters["+1/+0"] -= 1
            state.emit("Clockwork Avian: remove a +1/+0 counter (attacked)")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import available_mana_sources, can_afford, pay_cost

        if perm.tapped or state.phase != Phase.UPKEEP:
            return []
        have = perm.counters.get("+1/+0", 0)
        missing = 4 - have
        if missing <= 0:
            return []
        avail = len(available_mana_sources(state, {perm.uid})) + state.mana_pool.total()
        acts = []
        for x in range(1, min(missing, avail) + 1):
            cost = ManaCost(generic=x)
            if not can_afford(state, cost, exclude_uids={perm.uid}):
                break

            def build(xx, c=cost):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.tapped or not pay_cost(st, c, exclude_uids={p.uid}):
                        return False
                    p.tapped = True
                    return True

                def resolve(st):
                    p = st.find_permanent(perm.uid)
                    if p is not None:
                        add = min(xx, 4 - p.counters.get("+1/+0", 0))
                        p.counters["+1/+0"] = p.counters.get("+1/+0", 0) + add
                        st.emit(f"Clockwork Avian: add {add} +1/+0 counter(s)")
                    return None

                return CardAction.activated(
                    f"Clockwork Avian: {{{xx}}}, {{T}} — add {xx} +1/+0 counter(s)",
                    pay, resolve, source_name="Clockwork Avian",
                    ability_text="Put +1/+0 counters on Clockwork Avian")

            acts.append(build(x))
        return acts
