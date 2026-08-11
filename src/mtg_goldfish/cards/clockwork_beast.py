"""Clockwork Beast — {6} Artifact Creature — Beast 0/4.
Enters with seven +1/+0 counters (so a 7/4). At end of combat, if it attacked or
blocked, remove a +1/+0 counter. {X}, {T}: Put up to X +1/+0 counters on it (max
seven total); activate only during your upkeep.

Uses the generalised +1/+0 counter support in effective_power. The end-of-combat
removal fires via on_phase(END_COMBAT) if it attacked this turn; the upkeep
re-wind ability tops the counters back up (bounded to seven)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class ClockworkBeast(Card):
    card_name = "Clockwork Beast"
    trigger_phase = Phase.END_COMBAT

    def enters_with_counters(self, state):
        return {"+1/+0": 7}

    def on_phase(self, state, perm, phase):
        # "At end of combat, if it attacked or blocked this combat, remove one."
        if perm.turn_flags.get("attacked") and perm.counters.get("+1/+0", 0) > 0:
            perm.counters["+1/+0"] -= 1
            state.emit("Clockwork Beast: remove a +1/+0 counter (attacked)")
        return None

    def battlefield_actions(self, state, perm):
        from ..engine.actions import available_mana_sources, can_afford, pay_cost

        # {X}, {T}: put up to X +1/+0 counters (max total 7). Upkeep only.
        if perm.tapped or state.phase != Phase.UPKEEP:
            return []
        have = perm.counters.get("+1/+0", 0)
        missing = 7 - have
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
                        add = min(xx, 7 - p.counters.get("+1/+0", 0))
                        p.counters["+1/+0"] = p.counters.get("+1/+0", 0) + add
                        st.emit(f"Clockwork Beast: add {add} +1/+0 counter(s)")
                    return None

                return CardAction.activated(
                    f"Clockwork Beast: {{{xx}}}, {{T}} — add {xx} +1/+0 counter(s)",
                    pay, resolve, source_name="Clockwork Beast",
                    ability_text="Put +1/+0 counters on Clockwork Beast")

            acts.append(build(x))
        return acts
