"""Mahamoti Djinn
{4}{U}{U} Creature — Djinn 5/6. Flying.

Flying is auto from the keyword; otherwise a vanilla 5/6 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MahamotiDjinn(Card):
    card_name = "Mahamoti Djinn"
