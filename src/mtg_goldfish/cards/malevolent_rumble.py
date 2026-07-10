"""Malevolent Rumble — {1}{G} Sorcery.
Reveal the top four cards; put a permanent card from among them into your hand
(branch per distinct permanent revealed, plus none), the rest into your
graveyard. Create a 0/1 Eldrazi Spawn."""
from __future__ import annotations

from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard
from .base import Card, CardAction
from .registry import register


@register
class MalevolentRumble(Card):
    card_name = "Malevolent Rumble"

    def cast_actions(self, state):
        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def make(keep_name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                top = st.library[:4]
                kept = None
                for c in top:
                    if keep_name and c.name == keep_name and c.is_permanent and kept is None:
                        kept = c
                for c in top:
                    st.library.remove(c)
                    if c is kept:
                        st.hand.append(c)
                    else:
                        st.to_graveyard(c)
                st.make_token("Eldrazi Spawn", 0, 1, "Token Creature — Eldrazi Spawn")
                st.emit(f"Malevolent Rumble: dig 4, keep {kept.name if kept else 'nothing'}, Spawn token")
                return None
            return fn

        # Enumerate distinct permanent cards among the top four; plus "keep none".
        top = state.library[:4]
        names = sorted({c.name for c in top if c.is_permanent})
        return [CardAction(f"cast Malevolent Rumble (keep {n})", make(n)) for n in names] + \
               [CardAction("cast Malevolent Rumble (keep nothing)", make(None))]
