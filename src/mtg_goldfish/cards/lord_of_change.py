"""Lord of Change — {6}{U} 6/6 Flying, ward {3}. When it enters, draw three
cards."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class LordOfChange(Card):
    card_name = "Lord of Change"

    def on_etb(self, state, permanent):
        state.draw(3)
        state.emit(f"Lord of Change: draw three ({len(state.hand)} in hand)")
        return None
