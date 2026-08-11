"""Disenchant
{1}{W} Instant — Destroy target artifact or enchantment.
Only an opponent's permanent is worth destroying; there is none in a goldfish
(a rational player never targets their own), so this has no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Disenchant(Card):
    card_name = "Disenchant"
