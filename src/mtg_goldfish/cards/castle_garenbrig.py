"""Castle Garenbrig — Land.
Enters tapped unless you control a Forest. {T}: Add {G}.
{2}{G}{G}, {T}: Add six {G} — modelled as a battlefield action that fills the
pool. Approximation: the "spend only on creature spells/abilities"
restriction is ignored (the pool cannot carry restrictions); almost all mana
sinks in this deck are creatures."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ._common import controls_forest
from .base import Card, CardAction
from .registry import register


@register
class CastleGarenbrig(Card):
    card_name = "Castle Garenbrig"

    def etb_tapped(self, state):
        return not controls_forest(state)

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]

    def battlefield_actions(self, state, perm):
        cost = ManaCost.parse("{2}{G}{G}")
        # Castle Garenbrig must TAP for this ability, so it cannot also help pay
        # its own {2}{G}{G} cost — exclude it from the affordability check.
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def fn(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return None
            p.tapped = True  # pay the {T} first, before paying the mana cost
            if not pay_cost(st, cost, exclude_uids={perm.uid}):
                return None
            st.mana_pool.add("G", 6)
            st.emit("Castle Garenbrig: {2}{G}{G}, {T} — add {G}{G}{G}{G}{G}{G}")
            return None

        return [CardAction("Castle Garenbrig: add six {G}", fn)]
