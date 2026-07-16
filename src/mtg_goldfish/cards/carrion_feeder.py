"""Carrion Feeder — {B} Creature 1/1, can't block.
Sacrifice a creature: Put a +1/+1 counter on Carrion Feeder."""
from __future__ import annotations

from ._common import sacrifice_outlet_actions
from .base import Card
from .registry import register


@register
class CarrionFeeder(Card):
    card_name = "Carrion Feeder"

    def battlefield_actions(self, state, perm):
        def effect(st, src):
            if src is not None:
                src.counters["+1/+1"] = src.counters.get("+1/+1", 0) + 1
                st.emit(f"Carrion Feeder: +1/+1 counter "
                        f"({st.effective_power(src)}/{st.effective_toughness(src)})")
            return None

        return sacrifice_outlet_actions(
            self, state, perm, cost=None, effect=effect,
            label="Carrion Feeder: sacrifice a creature → +1/+1",
            sac_self_ok=False)
