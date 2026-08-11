"""White Knight
{W}{W} Creature — Human Knight 2/2. First strike, protection from black.

First strike is inert with no blockers; protection from black is inert with no
opposing black sources. A 2/2 body here (keywords auto)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WhiteKnight(Card):
    card_name = "White Knight"
