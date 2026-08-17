"""Triskelion — {6} Artifact Creature — Construct 1/1.
Enters with three +1/+1 counters on it.
Remove a +1/+1 counter from this creature: It deals 1 damage to any target.

Enters as a 4/4; each removed counter pings 1 (one branch per target: the
opponent, or a creature you control). No mana cost — repeatable while counters
remain."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class Triskelion(Card):
    card_name = "Triskelion"

    def enters_with_counters(self, state):
        return {"+1/+1": 3}

    def battlefield_actions(self, state, perm):
        if perm.counters.get("+1/+1", 0) <= 0:
            return []
        acts = []
        for suffix, apply in damage_any_target_options(state):
            def make(apply=apply):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.counters.get("+1/+1", 0) <= 0:
                        return False
                    p.counters["+1/+1"] -= 1
                    return True

                def resolve(st):
                    apply(st, 1)
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Triskelion: remove a +1/+1 counter → 1 damage to {suffix}",
                pay, resolve, source_name="Triskelion",
                ability_text="Remove a +1/+1 counter: deal 1 damage to any target"))
        return acts
