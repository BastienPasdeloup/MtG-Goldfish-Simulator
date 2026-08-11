"""Conservator
{4} Artifact — {3}, {T}: prevent the next 2 damage to you. No opponent damage in a goldfish — no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Conservator(Card):
    card_name = "Conservator"
