"""Stalactite Stalker — {B} Creature 1/1, menace.
At the beginning of your end step, if you descended this turn, put a +1/+1
counter on it.
{2}{B}, Sacrifice this creature: Target creature gets -X/-X until end of turn,
where X is this creature's power."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card, CardAction
from .registry import register


@register
class StalactiteStalker(Card):
    card_name = "Stalactite Stalker"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        if not state.descended_this_turn:
            return
        perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
        state.emit(f"Stalactite Stalker: descend +1/+1 "
                   f"({state.effective_power(perm)}/{state.effective_toughness(perm)})")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2, pips=(("B", 1),))
        if not can_afford(state, cost):
            return []
        x = state.effective_power(perm)
        if x <= 0:
            return []
        targets = {p.name: p.uid for p in state.battlefield
                   if p.is_creature_now and p.uid != perm.uid}
        if not targets:
            return []

        acts = []
        for tname, tuid in targets.items():

            def make(tuid=tuid, x=x):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    tgt = st.find_permanent(tuid)
                    if src is None or tgt is None or not pay_cost(st, cost):
                        return False
                    st.emit(f"sacrifice {src.name}")
                    st.leaves_battlefield(src, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    tgt = st.find_permanent(tuid)
                    if tgt is not None:
                        tgt.temp_power -= x
                        tgt.temp_toughness -= x
                        st.emit(f"Stalactite Stalker: {tgt.name} gets -{x}/-{x}")
                        st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Stalactite Stalker: sac → {tname} gets -{x}/-{x}",
                pay, resolve,
                source_name="Stalactite Stalker",
                ability_text=f"Target creature gets -{x}/-{x}"))
        return acts
