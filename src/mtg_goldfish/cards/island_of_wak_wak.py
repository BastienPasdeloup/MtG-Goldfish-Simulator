"""Island of Wak-Wak — Land.
{T}: Target creature with flying has base power 0 until end of turn.

The ability only weakens a flyer (an opponent's, in practice); it produces no mana.
Inert in a solitaire goldfish — the land is still played (counting as a land)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IslandOfWakWak(Card):
    card_name = "Island of Wak-Wak"
