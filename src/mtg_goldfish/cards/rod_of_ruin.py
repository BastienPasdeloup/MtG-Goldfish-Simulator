"""Rod of Ruin — {4} Artifact.
{3}, {T}: This artifact deals 1 damage to any target.

A repeatable pinger: {3}, {T} to deal 1 to the opponent or one of your creatures
(one branch per target)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class RodOfRuin(Card):
    card_name = "Rod of Ruin"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford

        cost = ManaCost(generic=3)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    from ..engine.actions import pay_cost
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    live.tapped = True
                    return True

                def resolve(st):
                    apply(st, 1)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Rod of Ruin: {{3}}, {{T}} → 1 damage to {suffix}",
                pay, resolve, source_name="Rod of Ruin",
                ability_text="Deal 1 damage to any target"))
        return acts
