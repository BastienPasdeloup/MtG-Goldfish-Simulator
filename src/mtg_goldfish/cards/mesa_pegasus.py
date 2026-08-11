"""Mesa Pegasus
{1}{W} Creature — Pegasus 1/1. Flying, banding.

Flying is auto from the keyword; banding is a combat-only ability with no effect
in a solitaire goldfish (no blockers). Effectively a 1/1 flyer."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MesaPegasus(Card):
    card_name = "Mesa Pegasus"
