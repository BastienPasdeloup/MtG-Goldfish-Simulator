"""Minamo, School at Water's Edge — Legendary Land.
{T}: Add {U}.
{U}, {T}: Untap target legendary permanent.

In this deck the untap ability is real value: untapping Emry lets you use her
graveyard-recursion again (one branch per legendary permanent you control)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Minamo(Card):
    card_name = "Minamo, School at Water's Edge"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("U", 1),))
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        acts = []
        seen: set[str] = set()
        for target in state.battlefield:
            if "legendary" not in target.type_line.lower() or not target.tapped:
                continue
            if target.name in seen:
                continue
            seen.add(target.name)

            def build(vuid, vname):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    victim = st.find_permanent(vuid)
                    if p is None or victim is None or p.tapped:
                        return False
                    p.tapped = True
                    if not pay_cost(st, cost, exclude_uids={p.uid}):
                        return False
                    return True

                def resolve(st):
                    victim = st.find_permanent(vuid)
                    if victim is not None:
                        victim.tapped = False
                        st.emit(f"Minamo: untap {vname}")
                    return None

                return CardAction.activated(
                    f"Minamo: {{U}}, {{T}} — untap {vname}",
                    pay, resolve, source_name="Minamo, School at Water's Edge",
                    ability_text="Untap target legendary permanent")

            acts.append(build(target.uid, target.name))
        return acts
