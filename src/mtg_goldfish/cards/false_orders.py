"""False Orders
{R} Instant — a defensive-combat trick against an opponent's blockers; none exist in a solitaire goldfish, so it is cast (counted) but has no board effect (structural)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class FalseOrders(Card):
    card_name = "False Orders"
