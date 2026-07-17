"""Cryptic Command — {1}{U}{U}{U} Instant. Choose two — counter a spell; return a
permanent to its owner's hand; tap all creatures opponents control; draw a card.
In a goldfish the useful modes are draw + bounce (of your own permanent, to reuse
an ETB); "draw only" (draw + tap-opponents) is also offered."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class CrypticCommand(Card):
    card_name = "Cryptic Command"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def make(bounce_uid):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                if bounce_uid is not None:
                    p = st.find_permanent(bounce_uid)
                    if p is not None:
                        st.emit(f"Cryptic Command: return {p.name} to hand")
                        st.leaves_battlefield(p, "hand")
                st.draw(1)
                st.emit("Cryptic Command: draw a card")
                return None
            return fn

        acts = [CardAction("cast Cryptic Command (draw + tap opponents)", make(None))]
        seen = set()
        for p in state.battlefield:
            if p.name not in seen and not p.is_token:
                seen.add(p.name)
                acts.append(CardAction(
                    f"cast Cryptic Command (draw + bounce {p.name})", make(p.uid)))
        return acts
