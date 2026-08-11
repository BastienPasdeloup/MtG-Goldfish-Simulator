"""Sengir Vampire
{3}{B}{B} Creature — Vampire 4/4. Flying.
Whenever a creature dealt damage by this creature this turn dies, put a +1/+1
counter on this creature.

Flying is auto. The counter trigger requires this creature to have damaged a
creature that then dies — it has no ping and combat damage in a goldfish only hits
the phantom opponent, so it effectively never fires here (a 4/4 flyer)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SengirVampire(Card):
    card_name = "Sengir Vampire"
