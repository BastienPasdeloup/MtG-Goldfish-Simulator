"""Snarling Gorehound — {B} Creature 1/1, menace.
Whenever another creature you control with power 2 or less enters, surveil 1."""
from __future__ import annotations

from ._common import surveil_branches
from .base import Card
from .registry import register


@register
class SnarlingGorehound(Card):
    card_name = "Snarling Gorehound"

    def on_other_etb(self, state, perm, entering):
        if (entering.uid != perm.uid and entering.is_creature_now
                and state.effective_power(entering) <= 2):
            return surveil_branches(state, 1, "Snarling Gorehound")
        return None
