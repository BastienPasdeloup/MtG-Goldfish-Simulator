"""Emperor of Bones — {1}{B} Creature 2/2, adapt.
At the beginning of combat on your turn, exile up to one target card from a
graveyard.
{1}{B}: Adapt 2 (if it has no +1/+1 counters, put two on it).
Whenever one or more +1/+1 counters are put on it, put a creature card exiled
with it onto the battlefield with a finality counter and haste; sacrifice it at
the beginning of the next end step. (Modelled as folded into its adapt: adapt is
the counter source in a goldfish.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import branch_over, enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class EmperorOfBones(Card):
    card_name = "Emperor of Bones"
    trigger_phase = Phase.BEGIN_COMBAT

    def on_phase(self, state, perm, phase):
        seen = set()
        gy_options = [("none", None)]
        for c in state.graveyard:
            if c.name not in seen:
                seen.add(c.name)
                gy_options.append((c.name, c.name))
        if len(gy_options) == 1:
            return None

        def fn(st, opt):
            _label, name = opt
            p = st.find_permanent(perm.uid)
            if name is None or p is None:
                st.emit("Emperor of Bones: exile nothing")
                return None
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is None:
                return None
            st.leave_graveyard(c)
            st.exile.append(c)
            p.exiled_with.append(c)
            st.emit(f"Emperor of Bones: exile {name} from graveyard")
            return None

        return branch_over(state, gy_options, fn)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("B", 1),))
        if perm.counters.get("+1/+1", 0) > 0 or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.counters.get("+1/+1", 0) > 0 or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is None:
                return None
            p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 2
            st.emit(f"Emperor of Bones: adapt 2 "
                    f"({st.effective_power(p)}/{st.effective_toughness(p)})")
            # Counters were put on → reanimate a creature card exiled with it.
            creature = next((c for c in p.exiled_with if c.is_creature), None)
            if creature is not None:
                p.exiled_with.remove(creature)
                if creature in st.exile:
                    st.exile.remove(creature)
                newp = enter_battlefield(
                    st, creature, announce=f"Emperor of Bones: reanimate {creature.name}")
                newp.counters["finality"] = 1
                newp.counters["end_step_sac"] = 1
                newp.temp_keywords.add("haste")
            return None

        return [CardAction.activated(
            "Emperor of Bones: adapt 2",
            pay, resolve,
            source_name="Emperor of Bones",
            ability_text="Adapt 2; reanimate an exiled creature card")]
