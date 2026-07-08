"""Lightning Bolt — {R} Instant. Deals 3 damage to any target: the (phantom)
opponent, yourself, or one of your creatures — each a branch."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card, CardAction
from .registry import register


@register
class LightningBolt(Card):
    card_name = "Lightning Bolt"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def player_fn(opponent: bool):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                if opponent:
                    st.opponent_life -= 3
                    st.emit(f"Lightning Bolt: 3 damage to opponent ({st.opponent_life})")
                else:
                    st.life -= 3
                    st.emit(f"Lightning Bolt: 3 damage to you ({st.life})")
                return None
            return fn

        actions = [
            CardAction("cast Lightning Bolt → opponent", player_fn(True)),
            CardAction("cast Lightning Bolt → yourself", player_fn(False)),
        ]

        def creature_effect(st, perm):
            perm.damage += 3
            st.emit(f"Lightning Bolt: 3 damage to {perm.name}")

        targets = [p.uid for p in state.battlefield if p.is_creature_now]
        actions.extend(targeted_instant_casts(self, state, targets, creature_effect))
        return actions
