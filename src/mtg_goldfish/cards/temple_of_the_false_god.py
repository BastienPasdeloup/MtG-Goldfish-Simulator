"""Temple of the False God — Land.
{T}: Add {C}{C} — only while you control five or more lands."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class TempleOfTheFalseGod(Card):
    card_name = "Temple of the False God"

    def mana_abilities(self, state):
        lands = sum(1 for p in state.battlefield if "land" in p.type_line.lower())
        if lands < 5:
            return []
        return [ManaAbility(amount=2, choices=("C",))]
