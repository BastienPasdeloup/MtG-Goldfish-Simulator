"""Claws of Gix — {0} Artifact.
{1}, Sacrifice a permanent: You gain 1 life.

A generic sacrifice outlet (any permanent, including itself), one branch per
distinct sacrificeable permanent."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import sacrifice_outlet_actions
from .base import Card
from .registry import register


@register
class ClawsOfGix(Card):
    card_name = "Claws of Gix"

    def battlefield_actions(self, state, perm):
        def gain_life(st, src):
            st.life += 1
            st.emit("Claws of Gix: gain 1 life")
            return None

        return sacrifice_outlet_actions(
            self, state, perm,
            cost=ManaCost(generic=1),
            effect=gain_life,
            label="Claws of Gix: {1}, sacrifice a permanent — gain 1 life",
            can_sac=lambda p: True,   # any permanent
            sac_self_ok=True,
        )
