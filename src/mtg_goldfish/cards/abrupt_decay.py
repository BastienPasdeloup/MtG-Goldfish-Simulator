"""Abrupt Decay — {B}{G} Instant. Destroy target nonland permanent with mana
value 3 or less. Only your own permanents are legal targets in solitaire."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class AbruptDecay(Card):
    card_name = "Abrupt Decay"

    def cast_actions(self, state):
        targets = [
            p.uid for p in state.battlefield
            if not p.is_land and p.card.cmc <= 3
        ]

        def effect(st, perm):
            st.emit(f"Abrupt Decay: destroy {perm.name}")
            st.leaves_battlefield(perm, "graveyard")

        return targeted_instant_casts(self, state, targets, effect)
