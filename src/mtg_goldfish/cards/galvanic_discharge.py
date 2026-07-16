"""Galvanic Discharge — {R} Instant. Choose target creature or planeswalker; you
get three energy, then you may pay any amount of energy; deal that much damage to
that permanent. (Pays all available energy for maximum damage.)"""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class GalvanicDischarge(Card):
    card_name = "Galvanic Discharge"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield if p.is_creature_now]

        def effect(st, perm):
            st.add_energy(3)
            x = st.energy
            st.pay_energy(x)
            perm.damage += x
            st.emit(f"Galvanic Discharge: {x} damage to {perm.name}")
            st.check_deaths()

        return targeted_instant_casts(self, state, targets, effect, tag="energy")
