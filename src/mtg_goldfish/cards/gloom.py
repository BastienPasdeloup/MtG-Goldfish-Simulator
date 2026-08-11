"""Gloom — {2}{B} Enchantment.
White spells cost {3} more to cast.
Activated abilities of white enchantments cost {3} more to activate.

The white-spell tax is modelled via cast_cost_increase ({3} more to cast any white
spell you play, on the generic cast path). The white-enchantment activated-ability
tax is not modelled (niche)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Gloom(Card):
    card_name = "Gloom"

    def cast_cost_increase(self, state, card):
        return 3 if "W" in (card.colors or []) else 0
