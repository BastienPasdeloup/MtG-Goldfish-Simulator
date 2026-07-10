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

    def phase_stack_items(self, state, perm, phase):
        if phase != Phase.UPKEEP:
            return []

        def resolve(st, uid=perm.uid):
            live = st.find_permanent(uid)
            if live is None:
                return None
            return live.impl.on_phase(st, live, Phase.UPKEEP)

        return [self.stack_ability(
            source_name=perm.name,
            label="Deadpool: upkeep",
            resolve=resolve,
            trigger_text="Beginning of your upkeep",
            ability_text="You lose 3 life",
        )]

    def on_phase(self, state, perm, phase):
        if phase == Phase.UPKEEP:
            state.life -= 3
            state.emit(f"Deadpool: lose 3 life ({state.life})")
