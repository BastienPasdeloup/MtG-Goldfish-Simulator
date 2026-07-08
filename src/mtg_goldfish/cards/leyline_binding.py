"""Leyline Binding — {5}{W} Enchantment, flash. Domain: costs {1} less per
basic land type among lands you control. Its ETB ("exile target nonland
permanent an opponent controls") has no target in solitaire — the trigger
fizzles, the enchantment stays. Castable for storm/enchantment purposes."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import basic_types_in_play
from .base import Card
from .registry import register


@register
class LeylineBinding(Card):
    card_name = "Leyline Binding"

    def cast_cost(self, state):
        return ManaCost(generic=max(0, 5 - basic_types_in_play(state)), pips=(("W", 1),))

    def on_etb(self, state, permanent):
        state.emit("Leyline Binding: no opponent permanent to exile (trigger fizzles)")
        return None
