"""Drain Power
{U}{U} Sorcery — Target player taps their lands for mana; you steal it.
Aimed at an opponent (none in a goldfish); targeting yourself is mana-neutral —
no useful effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DrainPower(Card):
    card_name = "Drain Power"
