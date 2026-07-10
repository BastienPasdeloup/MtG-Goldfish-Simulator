"""Planar Nexus — Land.
{T}: Add {C}. {1}, {T}: add one mana of any color (modelled as an alternative
mana ability with a generic surcharge folded in — the planner treats it as a
plain identity-color source, a slight overestimate only when {1} is tight).
Static "every nonbasic land type": honoured by Urza's Tower (Mine +
Power-Plant check); other type checks in this deck look for basics/Forests,
which Nexus is not."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class PlanarNexus(Card):
    card_name = "Planar Nexus"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost
        from ..engine.mana import ManaCost

        # Taps for this ability, so its own {T}:{C} can't help pay the {1}.
        if perm.tapped or not can_afford(state, ManaCost(generic=1), exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, ManaCost(generic=1), exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            color = any_identity_color(st)[0]
            st.mana_pool.add(color, 1)
            st.emit(f"Planar Nexus: {{1}}, {{T}} — add {{{color}}}")
            return None

        return [CardAction.activated(
            "Planar Nexus: {1}, {T} — any color",
            pay,
            resolve,
            source_name="Planar Nexus",
            ability_text="Add one mana of any color",
        )]
