"""Plague Rats — {2}{B} Creature — Rat */*.
Plague Rats's power and toughness are each equal to the number of creatures named
Plague Rats on the battlefield.

Dynamic P/T counting every Plague Rats on the battlefield (including itself)."""
from __future__ import annotations

from .base import Card
from .registry import register


def _rats(state) -> int:
    return sum(1 for p in state.battlefield if p.name == "Plague Rats")


@register
class PlagueRats(Card):
    card_name = "Plague Rats"

    def dynamic_power(self, state, perm):
        return _rats(state)

    def dynamic_toughness(self, state, perm):
        return _rats(state)
