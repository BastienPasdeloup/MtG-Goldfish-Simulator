"""Abundant Countryside — Land.
{T}: Add {C}.
{T}: Add one mana of any color (spend only on a creature spell — the restriction
is not enforced by the goldfish planner).
{6}, {T}: Create a 1/1 colorless Shapeshifter creature token with changeling."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class AbundantCountryside(Card):
    card_name = "Abundant Countryside"

    def mana_abilities(self, state):
        return [
            ManaAbility(amount=1, choices=("C",)),
            ManaAbility(amount=1, choices=any_identity_color(state)),
        ]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=6)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.make_token("Shapeshifter", 1, 1, "Creature — Shapeshifter",
                          text="Changeling (this token is every creature type).")
            st.emit("Abundant Countryside: create a 1/1 changeling Shapeshifter")
            return None

        return [CardAction.activated(
            "Abundant Countryside: make a 1/1 changeling",
            pay,
            resolve,
            source_name="Abundant Countryside",
            ability_text="Create a 1/1 colorless Shapeshifter with changeling",
        )]
