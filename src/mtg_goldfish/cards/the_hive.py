"""The Hive — {5} Artifact.
{5}, {T}: Create a 1/1 colorless Insect artifact creature token with flying named
Wasp.

A repeatable token maker: {5}, {T} makes a 1/1 flying Wasp."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class TheHive(Card):
    card_name = "The Hive"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=5)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            token = st.make_token("Wasp", 1, 1, "Artifact Creature — Insect",
                                  text="Flying")
            token.extra_keywords.add("flying")
            return None

        return [CardAction.activated(
            "The Hive: {5}, {T} — create a 1/1 flying Wasp",
            pay, resolve, source_name="The Hive",
            ability_text="Create a 1/1 flying Wasp token")]
