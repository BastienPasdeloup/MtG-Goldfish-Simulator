"""Prodigal Sorcerer — {2}{U} Creature — Human Wizard Sorcerer 1/1.
{T}: This creature deals 1 damage to any target.

The classic "Tim" pinger: {T} to deal 1 to the opponent or one of your creatures
(one branch per target)."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class ProdigalSorcerer(Card):
    card_name = "Prodigal Sorcerer"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick:
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    live = st.find_permanent(perm.uid)
                    if live is None or live.tapped or live.summoning_sick:
                        return False
                    live.tapped = True
                    return True

                def resolve(st):
                    apply(st, 1)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Prodigal Sorcerer: {{T}} → 1 damage to {suffix}",
                pay, resolve, source_name="Prodigal Sorcerer",
                ability_text="Deal 1 damage to any target"))
        return acts
