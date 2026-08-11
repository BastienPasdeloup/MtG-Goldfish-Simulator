"""Celestial Prism — {3} Artifact.
{2}, {T}: Add one mana of any color.

A colour filter (mana-negative on its own — {2} for 1 — but fixes colour). One
branch per colour in your commander identity (any_identity_color)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class CelestialPrism(Card):
    card_name = "Celestial Prism"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost):
            return []

        def build(color):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped:
                    return False
                p.tapped = True
                return pay_cost(st, cost)

            def resolve(st):
                st.mana_pool.add(color, 1)
                st.emit(f"Celestial Prism: add {{{color}}}")
                return None

            return CardAction.activated(
                f"Celestial Prism: {{2}}, {{T}} — add {{{color}}}",
                pay, resolve, source_name="Celestial Prism",
                ability_text="Add one mana of any color")

        return [build(c) for c in any_identity_color(state)]
