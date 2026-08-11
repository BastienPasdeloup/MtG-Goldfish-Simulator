"""Ghostfire Slice — {2}{R} Instant, devoid. Costs {2} less if an opponent
controls a multicolored permanent (never, against a phantom opponent). Deals 4
damage to any target."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card, CardAction
from .registry import register


@register
class GhostfireSlice(Card):
    card_name = "Ghostfire Slice"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def to_opponent(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            st.damage_opponent(4)  # noncombat -> amplifiers apply
            st.note_crime()
            st.emit(f"Ghostfire Slice: 4 damage to opponent ({st.opponent_life})")
            return None

        actions = [CardAction("cast Ghostfire Slice → opponent", to_opponent)]

        def creature_effect(st, perm):
            st.damage_permanent(perm, 4)
            st.emit(f"Ghostfire Slice: 4 damage to {perm.name}")
            st.check_deaths()

        targets = [p.uid for p in state.battlefield if p.is_creature_now]
        actions.extend(targeted_instant_casts(self, state, targets, creature_effect))
        return actions
