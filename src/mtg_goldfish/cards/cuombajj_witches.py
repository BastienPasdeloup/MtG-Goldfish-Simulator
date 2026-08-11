"""Cuombajj Witches — {B}{B} Creature — Human Wizard 1/3.
{T}: This creature deals 1 damage to any target and 1 damage to any target of an
opponent's choice.

{T} deals 1 to a target you choose (opponent or your creature) plus 1 to a target
the OPPONENT chooses — modelled as 1 to you (their best play against you)."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class CuombajjWitches(Card):
    card_name = "Cuombajj Witches"

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
                    apply(st, 1)                       # your choice
                    dealt = st.damage_self(1)          # opponent's choice (worst case: you)
                    st.emit(f"Cuombajj Witches: {dealt} damage to you (opponent's choice)")
                    st.check_deaths()
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Cuombajj Witches: {{T}} → 1 to {suffix}, 1 to you",
                pay, resolve, source_name="Cuombajj Witches",
                ability_text="Deal 1 to any target and 1 to a target of an opponent's choice"))
        return acts
