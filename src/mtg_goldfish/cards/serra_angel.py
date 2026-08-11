"""Serra Angel
{3}{W}{W} Creature — Angel 4/4. Flying, vigilance.

Both keywords are auto from the printed keywords; otherwise a vanilla 4/4."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SerraAngel(Card):
    card_name = "Serra Angel"
