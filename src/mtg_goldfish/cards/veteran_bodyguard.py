"""Veteran Bodyguard
{3}{W}{W} Creature — Human 2/5.
As long as this creature is untapped, all damage that would be dealt to you by
unblocked creatures is dealt to this creature instead.

The redirect only applies to an opponent's attackers, of which there are none in a
solitaire goldfish, so it is inert. A 2/5 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class VeteranBodyguard(Card):
    card_name = "Veteran Bodyguard"
