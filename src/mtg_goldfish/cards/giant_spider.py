"""Giant Spider
{3}{G} Creature — Spider 2/4. Reach.

Reach (blocks flyers) is inert with no attackers to block; the printed keyword
rides on the card. Effectively a vanilla body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GiantSpider(Card):
    card_name = "Giant Spider"
