"""Deadpool, Trading Card — {2}{B}{R} 5/3. At the beginning of your upkeep,
you lose 3 life. Not modelled: the text-box exchange (no meaningful text to
swap onto in solitaire) and "{3}, Sacrifice: each other player draws a card"
(only affects opponents)."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class DeadpoolTradingCard(Card):
    card_name = "Deadpool, Trading Card"

    def on_phase(self, state, perm, phase):
        if phase == Phase.UPKEEP:
            state.life -= 3
            state.emit(f"Deadpool: lose 3 life ({state.life})")
