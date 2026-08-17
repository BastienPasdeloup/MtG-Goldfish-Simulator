"""Reconstruction — {U} Sorcery.
Return target artifact card from your graveyard to your hand.

One branch per distinct artifact card in your graveyard."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Reconstruction(Card):
    card_name = "Reconstruction"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        names = []
        seen = set()
        for c in state.graveyard:
            if c.is_artifact and c.name not in seen:
                seen.add(c.name)
                names.append(c.name)
        if not names or not can_afford(state, cost):
            return []

        def make(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                for i, c in enumerate(st.graveyard):
                    if c.name == name and c.is_artifact:
                        st.hand.append(st.graveyard.pop(i))
                        st.emit(f"Reconstruction: return {name} to hand")
                        break
                return None
            return CardAction(f"cast Reconstruction → {name}", fn)

        return [make(n) for n in names]
