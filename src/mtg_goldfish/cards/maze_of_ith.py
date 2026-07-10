"""Maze of Ith — Land.
Produces no mana. Its untap-an-attacker ability is defensive (it matters
against opponents' attacks, which don't exist in a goldfish); untapping your
own attacker after damage is not modelled — the card is a no-op land here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MazeOfIth(Card):
    card_name = "Maze of Ith"
