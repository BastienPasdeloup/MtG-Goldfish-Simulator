"""Night Nurse, Healer of Heroes — {1}{W} 2/1 flash, lifelink.
ETB: return target permanent card put into your graveyard this turn to your
hand (branch; fizzles with no target)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class NightNurse(Card):
    card_name = "Night Nurse, Healer of Heroes"

    def on_etb(self, state, permanent):
        eligible = sorted({
            c.name for c in state.graveyard
            if c.is_permanent and c.name in state.gy_this_turn
        })
        if not eligible:
            return None

        def apply(st, name: str):
            card = next(c for c in st.graveyard if c.name == name)
            st.graveyard.remove(card)
            st.hand.append(card)
            st.emit(f"Night Nurse: return {name} to hand")

        return branch_over(state, eligible, apply)
