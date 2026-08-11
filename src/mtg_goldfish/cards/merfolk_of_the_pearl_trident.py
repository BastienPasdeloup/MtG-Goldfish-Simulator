"""Merfolk of the Pearl Trident
{U} Creature — Merfolk 1/1. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MerfolkOfThePearlTrident(Card):
    card_name = "Merfolk of the Pearl Trident"
