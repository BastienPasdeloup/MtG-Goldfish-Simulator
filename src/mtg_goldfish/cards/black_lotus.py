"""Black Lotus — {0} Artifact.
{T}, Sacrifice this artifact: Add three mana of any one color.

One branch per colour in your commander identity (any colour is legal, but
off-identity mana is useless in a Commander goldfish — see any_identity_color)."""
from __future__ import annotations

from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class BlackLotus(Card):
    card_name = "Black Lotus"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def build(color):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped:
                    return False
                p.tapped = True
                st.leaves_battlefield(p, "graveyard", reason="sacrifice")
                return True

            def resolve(st):
                st.mana_pool.add(color, 3)
                st.emit(f"Black Lotus: add {{{color}}}{{{color}}}{{{color}}}")
                return None

            return CardAction.activated(
                f"Black Lotus: {{T}}, sacrifice — add three {{{color}}}",
                pay, resolve, source_name="Black Lotus",
                ability_text="Add three mana of any one color")

        return [build(c) for c in any_identity_color(state)]
