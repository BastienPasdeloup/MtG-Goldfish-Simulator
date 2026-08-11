"""Aladdin's Ring — {8} Artifact.
{8}, {T}: This artifact deals 4 damage to any target.

A pricey repeatable pinger: {8}, {T} to deal 4 to the opponent or one of your
creatures (one branch per target)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class AladdinsRing(Card):
    card_name = "Aladdin's Ring"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=8)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                        return False
                    live.tapped = True
                    return True

                def resolve(st):
                    apply(st, 4)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Aladdin's Ring: {{8}}, {{T}} → 4 damage to {suffix}",
                pay, resolve, source_name="Aladdin's Ring",
                ability_text="Deal 4 damage to any target"))
        return acts
