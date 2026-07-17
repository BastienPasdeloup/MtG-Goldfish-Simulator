"""Drown in the Loch — {U}{B} Instant. Choose one — counter a spell with mana
value ≤ cards in its controller's graveyard; or destroy a creature with mana
value ≤ cards in its controller's graveyard. Only the destroy mode (on your own
creatures, gated by your graveyard size) is usable in a goldfish."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class DrownInTheLoch(Card):
    card_name = "Drown in the Loch"

    def cast_actions(self, state):
        limit = len(state.graveyard)
        targets = [p.uid for p in state.battlefield
                   if p.is_creature_now and p.card.cmc <= limit]

        def effect(st, perm):
            if perm.card.cmc <= len(st.graveyard):
                st.emit(f"Drown in the Loch: destroy {perm.name}")
                st.leaves_battlefield(perm, "graveyard", reason="destroy")

        return targeted_instant_casts(self, state, targets, effect,
                                      tag=f"mv≤{limit} in graveyard")
