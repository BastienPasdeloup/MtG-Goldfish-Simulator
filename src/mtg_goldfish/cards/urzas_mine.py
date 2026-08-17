"""Urza's Mine — Land — Urza's Mine.
{T}: Add {C}. If you control an Urza's Power-Plant and an Urza's Tower, add {C}{C}
instead.

Tron: taps for 2 colourless once all three Urzatron pieces are assembled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class UrzasMine(Card):
    card_name = "Urza's Mine"

    def mana_abilities(self, state):
        full = (state.has_permanent_named("Urza's Power Plant")
                and state.has_permanent_named("Urza's Tower"))
        return [ManaAbility(amount=2 if full else 1, choices=("C",))]
