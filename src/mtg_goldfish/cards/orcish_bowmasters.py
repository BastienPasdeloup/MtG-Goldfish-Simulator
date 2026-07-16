"""Orcish Bowmasters — {1}{B} Creature 1/1, flash.
When this creature enters and whenever an opponent draws a card (except the
first in their draw step), it deals 1 damage to any target, then amass Orcs 1.
Against a phantom opponent only the ETB half fires."""
from __future__ import annotations

from ._common import amass, branch_over, damage_any_target_options
from .base import Card
from .registry import register


@register
class OrcishBowmasters(Card):
    card_name = "Orcish Bowmasters"

    def on_etb(self, state, permanent):
        def fn(st, opt):
            suffix, apply = opt
            apply(st, 1)
            amass(st, 1, "Orc")
            st.emit(f"Orcish Bowmasters: 1 damage to {suffix}, amass Orcs 1")
            return None

        return branch_over(state, damage_any_target_options(state), fn)
