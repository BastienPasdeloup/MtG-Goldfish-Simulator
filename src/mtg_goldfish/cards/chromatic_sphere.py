"""Chromatic Sphere — {1} Artifact.
{1}, {T}, Sacrifice this artifact: Add one mana of any color. Draw a card.

The sacrifice puts it into the graveyard (so Emry can recur it); "any color" is
restricted to the commander identity (any_identity_color)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class ChromaticSphere(Card):
    card_name = "Chromatic Sphere"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost):
            return []

        def build(color):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost):
                    return False
                st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                return True

            def resolve(st):
                st.mana_pool.add(color, 1)
                st.emit(f"Chromatic Sphere: add {{{color}}}, draw a card")
                st.draw(1)
                return None

            return CardAction.activated(
                f"Chromatic Sphere: sacrifice — add {{{color}}}, draw",
                pay, resolve, source_name="Chromatic Sphere",
                ability_text="Add one mana of any color, draw a card")

        return [build(c) for c in any_identity_color(state)]
