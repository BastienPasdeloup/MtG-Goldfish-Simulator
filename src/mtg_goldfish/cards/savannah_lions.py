"""Savannah Lions
{W} Creature — Cat 2/1. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SavannahLions(Card):
    card_name = "Savannah Lions"
