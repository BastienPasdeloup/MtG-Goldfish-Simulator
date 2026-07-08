"""Tishana's Tidebinder — {2}{U} 3/2 flash. ETB: counter up to one target
activated or triggered ability — nothing can be responded to in this solitaire
engine (abilities resolve atomically), so the trigger always fizzles (exact)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TishanasTidebinder(Card):
    card_name = "Tishana's Tidebinder"

    def on_etb(self, state, permanent):
        state.emit("Tishana's Tidebinder: no ability to counter (trigger fizzles)")
        return None
