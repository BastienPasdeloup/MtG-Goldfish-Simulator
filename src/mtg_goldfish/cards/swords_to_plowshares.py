"""Swords to Plowshares — {W} Instant. Exile target creature; its controller
gains life equal to its power. Only your own creatures are legal targets in a
solitaire game (so you gain the life)."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class SwordsToPlowshares(Card):
    card_name = "Swords to Plowshares"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield if p.is_creature_now]

        def effect(st, perm):
            gained = max(0, st.effective_power(perm))
            st.leaves_battlefield(perm, "exile")
            st.life += gained
            st.emit(f"Swords to Plowshares: exile {perm.name}, gain {gained} life")

        return targeted_instant_casts(self, state, targets, effect)
