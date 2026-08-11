"""Two-Headed Giant of Foriys
{4}{R} Creature — Giant 4/4. Trample.
This creature can block an additional creature each combat.

Trample is auto; the extra-block clause is inert with no attackers to block.
Effectively a 4/4 trampler."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TwoHeadedGiantOfForiys(Card):
    card_name = "Two-Headed Giant of Foriys"
