"""Argivian Blacksmith — {1}{W}{W} Creature — Human Artificer 2/2.
{T}: Prevent the next 2 damage that would be dealt to target artifact creature
this turn.

Prevents damage to a CREATURE, but a goldfish deals no damage to your creatures
(no opposing attackers/blockers), so the ability is fully inert — a fixed 2/2
body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ArgivianBlacksmith(Card):
    card_name = "Argivian Blacksmith"
