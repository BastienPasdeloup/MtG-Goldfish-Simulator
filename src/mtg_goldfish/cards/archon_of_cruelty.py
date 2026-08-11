"""Archon of Cruelty — {6}{B}{B} 6/6 Flying. Whenever it enters or attacks, target
opponent sacrifices a creature or planeswalker, discards a card, and loses 3 life;
you draw a card and gain 3 life. Against a phantom opponent only the life loss /
your draw + lifegain apply (they have nothing to sacrifice or discard)."""
from __future__ import annotations

from .base import Card
from .registry import register


def _trigger(state):
    state.opponent_life -= 3
    state.draw(1)
    state.gain_life(3)
    state.note_crime()
    state.emit(f"Archon of Cruelty: opponent loses 3, you draw a card and gain 3 "
               f"(you {state.life}, opp {state.opponent_life})")


@register
class ArchonOfCruelty(Card):
    card_name = "Archon of Cruelty"

    def on_etb(self, state, permanent):
        _trigger(state)
        return None

    def on_attack(self, state, perm):
        _trigger(state)
