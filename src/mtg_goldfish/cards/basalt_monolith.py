"""Basalt Monolith — {3} Artifact.
This artifact doesn't untap during your untap step.
{T}: Add {C}{C}{C}.
{3}: Untap this artifact.

Modelled exactly: it taps for three colourless, stays tapped through the untap
step (skips_untap), and can be untapped for {3} (mana-neutral by itself)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import artifact_ability_cost
from .base import Card, CardAction
from .registry import register


@register
class BasaltMonolith(Card):
    card_name = "Basalt Monolith"

    def skips_untap(self, state, perm):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=3, choices=("C",))]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if not perm.tapped:
            return []  # "{3}: Untap" is only meaningful while it is tapped
        cost = artifact_ability_cost(state, ManaCost(generic=3))
        # It is tapped, so it can't help pay its own untap cost anyway.
        if not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not p.tapped or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.tapped = False
                st.emit("Basalt Monolith: untap")
            return None

        return [CardAction.activated(
            "Basalt Monolith: {3} — untap",
            pay,
            resolve,
            source_name="Basalt Monolith",
            ability_text="Untap Basalt Monolith",
        )]
