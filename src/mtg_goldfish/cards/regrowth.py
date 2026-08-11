"""Regrowth — {1}{G} Sorcery.
Return target card from your graveyard to your hand.

One branch per distinct card in your graveyard (any type)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Regrowth(Card):
    card_name = "Regrowth"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        acts = []
        seen: set[str] = set()
        for c in state.graveyard:
            if c.name in seen:
                continue
            seen.add(c.name)

            def make(target=c):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or target not in st.graveyard or not begin_cast(st, card, self.mana_cost):
                        return None
                    resolve_to_graveyard(st, card)
                    st.graveyard.remove(target)
                    st.hand.append(target)
                    st.emit(f"Regrowth: return {target.name} to hand")
                    return None
                return fn

            acts.append(CardAction(f"cast Regrowth → {c.name}", make()))
        return acts
