"""Ashnod's Altar — {3} Artifact.
Sacrifice a creature: Add {C}{C}.

A free sacrifice-for-mana outlet: one branch per distinct creature you control."""
from __future__ import annotations

from ._common import sacrifice_outlet_actions
from .base import Card
from .registry import register


@register
class AshnodsAltar(Card):
    card_name = "Ashnod's Altar"

    def battlefield_actions(self, state, perm):
        def effect(st, src):
            st.mana_pool.add("C", 2)
            st.emit("Ashnod's Altar: add {C}{C}")
            return None

        return sacrifice_outlet_actions(
            self, state, perm, cost=None, effect=effect,
            label="Ashnod's Altar: sacrifice a creature — add {C}{C}")
