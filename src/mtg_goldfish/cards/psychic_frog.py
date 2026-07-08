"""Psychic Frog — {U}{B} 1/2. Combat damage: draw a card. Discard a card:
+1/+1 counter (branch per distinct card). Exile three cards from your
graveyard: flying until end of turn (no blockers exist — no effect, omitted)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class PsychicFrog(Card):
    card_name = "Psychic Frog"

    def on_combat_damage(self, state, perm, damage):
        state.emit("Psychic Frog: combat damage — draw a card")
        state.draw(1)

    def battlefield_actions(self, state, perm):
        seen: set[str] = set()
        actions = []
        for card in state.hand:
            if card.name in seen:
                continue
            seen.add(card.name)

            def make(name: str):
                def fn(st):
                    p = st.find_permanent(perm.uid)
                    c = next((x for x in st.hand if x.name == name), None)
                    if p is None or c is None:
                        return None
                    st.hand.remove(c)
                    st.to_graveyard(c)
                    p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
                    st.emit(f"Psychic Frog: discard {name} — +1/+1 counter")
                    return None
                return fn

            actions.append(CardAction(f"Psychic Frog: discard {card.name}", make(card.name)))
        return actions
