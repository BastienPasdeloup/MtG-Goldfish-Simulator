"""Arcum's Astrolabe — {S} Snow Artifact.
When it enters, draw a card.
{1}, {T}: Add one mana of any color.

{S} (one snow mana) is approximated as {1} generic (snow sources aren't tracked
in this engine). "Any color" is restricted to the commander identity, where the
filter is actually useful (see any_identity_color)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class ArcumsAstrolabe(Card):
    card_name = "Arcum's Astrolabe"

    def cast_cost(self, state):
        return ManaCost(generic=1)  # {S} approximated as one generic mana

    def on_etb(self, state, permanent):
        state.draw(1)
        state.emit("Arcum's Astrolabe: draw a card")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost):
            return []

        def build(color):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped:
                    return False
                p.tapped = True
                if not pay_cost(st, cost):
                    return False
                return True

            def resolve(st):
                st.mana_pool.add(color, 1)
                st.emit(f"Arcum's Astrolabe: add {{{color}}}")
                return None

            return CardAction.activated(
                f"Arcum's Astrolabe: {{1}}, {{T}} — add {{{color}}}",
                pay, resolve, source_name="Arcum's Astrolabe",
                ability_text="Add one mana of any color")

        return [build(c) for c in any_identity_color(state)]
