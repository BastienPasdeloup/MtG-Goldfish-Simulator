"""Hill Giant
{3}{R} Creature — Giant 3/3. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HillGiant(Card):
    card_name = "Hill Giant"
