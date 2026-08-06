"""Chromatic Star — {1} Artifact.
{1}, {T}, Sacrifice this artifact: Add one mana of any color.
When this artifact is put into a graveyard from the battlefield, draw a card.

Like Chromatic Sphere but the draw is a DEATH trigger (on_leave) rather than
part of the mana ability — so it also draws if it dies some other way. In a
solitaire game the only way it leaves is its own sacrifice (to the graveyard),
so the net effect matches Chromatic Sphere."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class ChromaticStar(Card):
    card_name = "Chromatic Star"

    def on_leave(self, state, permanent):
        # "When ~ is put into a graveyard from the battlefield, draw a card."
        state.draw(1)
        state.emit("Chromatic Star: draw a card")

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
                # To the graveyard — triggers the "draw a card" leave ability.
                st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                return True

            def resolve(st):
                st.mana_pool.add(color, 1)
                st.emit(f"Chromatic Star: add {{{color}}}")
                return None

            return CardAction.activated(
                f"Chromatic Star: sacrifice — add {{{color}}}",
                pay, resolve, source_name="Chromatic Star",
                ability_text="Add one mana of any color")

        return [build(c) for c in any_identity_color(state)]
