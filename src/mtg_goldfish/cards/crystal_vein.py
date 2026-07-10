"""Crystal Vein — Land.
{T}: Add {C}. {T}, Sacrifice: add {C}{C} (battlefield action; the mana goes
to the pool, usable this phase — the payment planner does not anticipate it)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class CrystalVein(Card):
    card_name = "Crystal Vein"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            st.leaves_battlefield(p, "graveyard")
            return True

        def resolve(st):
            st.mana_pool.add("C", 2)
            st.emit("Crystal Vein: sacrifice — add {C}{C}")
            return None

        return [CardAction.activated(
            "Crystal Vein: sacrifice for {C}{C}",
            pay,
            resolve,
            source_name="Crystal Vein",
            ability_text="Add {C}{C}",
        )]
