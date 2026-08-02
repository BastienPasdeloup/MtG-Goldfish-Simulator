"""Serrated Scorpion — {B} Creature 1/2. When it dies, it deals 2 damage to each
opponent and you gain 2 life."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SerratedScorpion(Card):
    card_name = "Serrated Scorpion"

    def on_leave(self, state, permanent):
        state.damage_opponent(2)  # noncombat -> amplifiers apply
        state.life += 2
        state.emit(f"Serrated Scorpion dies: 2 damage to opponent "
                   f"({state.opponent_life}), gain 2 life ({state.life})")
