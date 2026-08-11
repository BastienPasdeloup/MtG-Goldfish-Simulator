"""Painter's Servant — {2} Artifact Creature — Scarecrow 1/3.
As this creature enters, choose a color.
All cards that aren't on the battlefield, spells, and permanents are the chosen
color in addition to their other colors.

The chosen colour is stored on the permanent (perm.chosen); `painter_colors`
exposes it to colour-matters effects. The key interaction here is with Grindstone
(every card then shares a colour, so it mills the whole library into the
graveyard — huge for Emry). One ETB branch per colour."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class PaintersServant(Card):
    card_name = "Painter's Servant"

    def enter_choices(self, state, perm):
        def fn(st, color):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.chosen = color
                st.emit(f"Painter's Servant: choose {color}")
            return None

        return branch_over(state, ["W", "U", "B", "R", "G"], fn)
