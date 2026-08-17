"""Sage of Lat-Nam — {1}{U} Creature — Human Artificer 1/2.
{T}, Sacrifice an artifact: Draw a card.

One branch per distinct artifact; taps."""
from __future__ import annotations

from ._common import sacrifice_outlet_actions
from .base import Card
from .registry import register


@register
class SageOfLatNam(Card):
    card_name = "Sage of Lat-Nam"

    def battlefield_actions(self, state, perm):
        def effect(st, src):
            st.draw(1)
            st.emit("Sage of Lat-Nam: draw a card")
            return None

        return sacrifice_outlet_actions(
            self, state, perm, cost=None, effect=effect, tap=True,
            label="Sage of Lat-Nam: {T}, sacrifice an artifact — draw a card",
            can_sac=lambda p: p.is_artifact)
