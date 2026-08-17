"""Atog — {1}{R} Creature — Atog 1/2.
Sacrifice an artifact: This creature gets +2/+2 until end of turn.

One branch per distinct artifact you control; repeatable (the search stacks it)."""
from __future__ import annotations

from ._common import sacrifice_outlet_actions
from .base import Card
from .registry import register


@register
class Atog(Card):
    card_name = "Atog"

    def battlefield_actions(self, state, perm):
        def effect(st, src):
            if src is not None:
                src.temp_power += 2
                src.temp_toughness += 2
                st.emit("Atog: +2/+2 until end of turn")
            return None

        return sacrifice_outlet_actions(
            self, state, perm, cost=None, effect=effect,
            label="Atog: sacrifice an artifact — +2/+2 until end of turn",
            can_sac=lambda p: p.is_artifact)
