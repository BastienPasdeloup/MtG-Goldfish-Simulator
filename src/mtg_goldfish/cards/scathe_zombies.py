"""Scathe Zombies
{2}{B} Creature — Zombie 2/2. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ScatheZombies(Card):
    card_name = "Scathe Zombies"
