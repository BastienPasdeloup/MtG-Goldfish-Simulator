"""Orcish Oriflamme — {3}{R} Enchantment.
Attacking creatures you control get +1/+0.

A conditional anthem via static_pt_bonus: every creature currently attacking (its
uid is in state.attackers) gets +1/+0."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class OrcishOriflamme(Card):
    card_name = "Orcish Oriflamme"

    def static_pt_bonus(self, state, source, perm):
        if perm.is_creature_now and perm.uid in state.attackers:
            return (1, 0)
        return (0, 0)
