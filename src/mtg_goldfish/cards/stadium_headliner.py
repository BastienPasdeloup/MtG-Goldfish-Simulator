"""Stadium Headliner — {R} Creature 1/1.
Mobilize 1 (Whenever it attacks, create a tapped and attacking 1/1 red Warrior
token; sacrifice it at the beginning of the next end step.)
{1}{R}, Sacrifice this creature: It deals damage equal to the number of creatures
you control to target creature."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class StadiumHeadliner(Card):
    card_name = "Stadium Headliner"

    def on_attack(self, state, perm):
        tok = state.make_token("Warrior", 1, 1, "Creature — Warrior",
                               tapped=True, attacking=True)
        tok.counters["end_step_sac"] = 1
        state.emit("Stadium Headliner: mobilize — tapped, attacking 1/1 Warrior")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("R", 1),))
        if not can_afford(state, cost):
            return []
        targets = {p.name: p.uid for p in state.battlefield
                   if p.is_creature_now and p.uid != perm.uid}
        if not targets:
            return []

        acts = []
        for tname, tuid in targets.items():

            def make(tuid=tuid):
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
                        x = st.creatures_in_play()
                        tgt.damage += x
                        st.emit(f"Stadium Headliner: {x} damage to {tgt.name}")
                        st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Stadium Headliner: sac → damage {tname}",
                pay, resolve,
                source_name="Stadium Headliner",
                ability_text="Deal damage equal to creatures you control"))
        return acts
