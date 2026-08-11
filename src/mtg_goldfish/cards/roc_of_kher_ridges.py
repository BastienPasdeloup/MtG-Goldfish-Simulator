"""Roc of Kher Ridges
{3}{R} Creature — Bird 3/3. Flying.

Flying is auto from the keyword; otherwise a vanilla 3/3."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class RocOfKherRidges(Card):
    card_name = "Roc of Kher Ridges"
