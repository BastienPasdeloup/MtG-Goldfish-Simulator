"""Shifting Woodland — Land.
Enters tapped unless you control a Forest. {T}: Add {G}.
Delirium — {2}{G}{G}: This land becomes a copy of target permanent card in your
graveyard until end of turn. Activate only if there are four or more card types
among cards in your graveyard.

Modelled via GameState.become_copy_until_eot (full copy — name, types, P/T and
abilities — reverting at cleanup). Branches over each distinct permanent card in
the graveyard. Its own {G} mana ability is paid BEFORE the copy (so the ability
excludes Shifting Woodland from the payment, leaving the copy untapped to act)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import controls_forest, graveyard_card_types
from .base import Card, CardAction
from .registry import register

_COPY_COST = ManaCost(generic=2, pips=(("G", 2),))


@register
class ShiftingWoodland(Card):
    card_name = "Shifting Woodland"

    def etb_tapped(self, state):
        return not controls_forest(state)

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.becomes is not None:                        # already a copy this turn
            return []
        if len(graveyard_card_types(state)) < 4:            # delirium
            return []
        if not can_afford(state, _COPY_COST, exclude_uids={perm.uid}):
            return []
        seen: set[str] = set()
        acts: list[CardAction] = []
        for src in state.graveyard:
            if not src.is_permanent or src.name in seen:
                continue
            seen.add(src.name)

            def make(name=src.name):
                def pay(st):
                    p = st.find_permanent(perm.uid)
                    if p is None or p.becomes is not None:
                        return False
                    # Keep Shifting Woodland untapped so the copy can act.
                    return pay_cost(st, _COPY_COST, exclude_uids={p.uid})

                def resolve(st):
                    p = st.find_permanent(perm.uid)
                    target = next((c for c in st.graveyard if c.name == name), None)
                    if p is None or target is None:
                        return None
                    st.become_copy_until_eot(p, target)
                    st.emit(f"Shifting Woodland becomes a copy of {name} until end of turn")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Shifting Woodland: become a copy of {src.name}", pay, resolve,
                source_name="Shifting Woodland",
                ability_text="Delirium — become a copy of a permanent card in your graveyard (EOT)"))
        return acts
