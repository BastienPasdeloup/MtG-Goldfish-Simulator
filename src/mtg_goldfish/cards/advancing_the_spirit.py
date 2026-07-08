"""Advancing the Spirit — {2}{G} Enchantment. When it enters, draw a card.
"You may pay {0} rather than the power-up cost of the first power-up ability
you activate each turn" — consumed by Nick Fury's power-up (see nick_fury)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AdvancingTheSpirit(Card):
    card_name = "Advancing the Spirit"

    def on_etb(self, state, permanent):
        state.draw(1)
        state.emit("Advancing the Spirit: draw a card")
        return None
