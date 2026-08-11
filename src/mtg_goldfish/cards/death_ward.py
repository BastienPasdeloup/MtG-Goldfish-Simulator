"""Death Ward
{W} Instant — Regenerate target creature.
Regeneration only matters against destruction, of which there is none in a
solitaire goldfish — no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DeathWard(Card):
    card_name = "Death Ward"
