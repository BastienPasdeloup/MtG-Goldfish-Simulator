"""Gaea's Avenger — {1}{G}{G} Creature — Treefolk 1+*/1+*.
Power and toughness are each equal to 1 plus the number of artifacts your
opponents control.

The phantom opponent controls no artifacts in a goldfish, so it is a 1/1
(characteristic-defining, so P/T must be supplied dynamically)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GaeasAvenger(Card):
    card_name = "Gaea's Avenger"

    def dynamic_power(self, state, perm):
        return 1  # 1 + opponents' artifacts (0 in a goldfish)

    def dynamic_toughness(self, state, perm):
        return 1
