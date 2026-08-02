"""Ba Sing Se — Land.
Enters tapped unless you control a basic land. {T}: Add {G}.
{2}{G}, {T}: Earthbend 2 — put two +1/+1 counters on target land you control;
it becomes a 0/0 creature with haste that's still a land (a permanent 2/2 land
creature). Activate only as a sorcery. The animation persists across turns (a
`permanent` becomes-animation that cleanup does not clear)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from ._common import _creature_type_line
from .registry import register

_EARTHBEND_COST = ManaCost(generic=2, pips=(("G", 1),))


@register
class BaSingSe(Card):
    card_name = "Ba Sing Se"

    def etb_tapped(self, state):
        return not any(
            "basic" in p.type_line.lower() and p.is_land
            for p in state.battlefield
        )

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped:
            return []
        # Ba Sing Se taps for {T}, so it can't also pay its own {2}{G}.
        if not can_afford(state, _EARTHBEND_COST, exclude_uids={perm.uid}):
            return []
        # Target land you control: offer each distinct untapped land that isn't
        # already a creature (re-animating adds nothing useful in a goldfish).
        targets, seen = [], set()
        for p in state.battlefield:
            if (p.uid != perm.uid and p.is_land and not p.tapped
                    and not p.is_creature_now and p.name not in seen):
                seen.add(p.name)
                targets.append(p)
        acts = []
        for t in targets:
            def make(tuid=t.uid, tname=t.name):
                def pay(st):
                    bs = st.find_permanent(perm.uid)
                    if bs is None or bs.tapped:
                        return False
                    # Exclude Ba Sing Se ({T} cost) and the target (must stay
                    # untapped to attack) from the mana payment.
                    if not pay_cost(st, _EARTHBEND_COST,
                                    exclude_uids={bs.uid, tuid}):
                        return False
                    bs.tapped = True
                    return True

                def resolve(st):
                    land = st.find_permanent(tuid)
                    if land is None:
                        return None
                    land.becomes = {
                        "type_line": _creature_type_line(land.type_line),
                        "power": 0, "toughness": 0, "permanent": True,
                    }
                    land.counters["+1/+1"] = land.counters.get("+1/+1", 0) + 2
                    land.extra_keywords.add("haste")
                    land.summoning_sick = False
                    st.emit(f"Ba Sing Se: earthbend 2 → {tname} becomes a "
                            f"2/2 land creature with haste")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Ba Sing Se: earthbend 2 → {t.name}", pay, resolve,
                sorcery_speed=True, source_name=self.card_name,
                ability_text="Earthbend 2 (target land becomes a 2/2 haste land creature)"))
        return acts
