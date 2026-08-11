"""Healing Salve — {W} Instant.
Choose one —
• Target player gains 3 life.
• Prevent the next 3 damage that would be dealt to any target this turn.

Two branches: gain 3 life (you), or add a 3-damage prevention shield for yourself
(any colour). Both are genuinely useful in a goldfish."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class HealingSalve(Card):
    card_name = "Healing Salve"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, resolve_to_graveyard

        def make(mode):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, self.mana_cost):
                    return None
                resolve_to_graveyard(st, card)
                if mode == "life":
                    st.gain_life(3)
                    st.emit("Healing Salve: gain 3 life")
                else:
                    st.prevent_shields.append((3, None))
                    st.emit("Healing Salve: prevent next 3 damage to you this turn")
                return None
            return fn

        return [
            CardAction("cast Healing Salve → gain 3 life", make("life")),
            CardAction("cast Healing Salve → prevent 3 damage", make("prevent")),
        ]
