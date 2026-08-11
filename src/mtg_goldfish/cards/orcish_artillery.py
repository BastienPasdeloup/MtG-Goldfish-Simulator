"""Orcish Artillery — {1}{R}{R} Creature — Orc Warrior 1/3.
{T}: This creature deals 2 damage to any target and 3 damage to you.

A pinger with a painful kickback: {T} deals 2 to a target (opponent or your
creature) plus 3 to yourself (via damage_self, red source)."""
from __future__ import annotations

from ._common import damage_any_target_options
from .base import Card, CardAction
from .registry import register


@register
class OrcishArtillery(Card):
    card_name = "Orcish Artillery"

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
                    apply(st, 2)
                    dealt = st.damage_self(3, colors=("R",))
                    st.emit(f"Orcish Artillery: {dealt} damage to you")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Orcish Artillery: {{T}} → 2 damage to {suffix}, 3 to you",
                pay, resolve, source_name="Orcish Artillery",
                ability_text="Deal 2 damage to any target and 3 damage to you"))
        return acts
