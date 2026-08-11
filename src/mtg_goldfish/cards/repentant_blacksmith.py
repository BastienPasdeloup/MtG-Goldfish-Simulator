"""Repentant Blacksmith
{1}{W} Creature — Human 1/2. Protection from red.

Protection from red is inert in a solitaire goldfish (no opposing red sources).
A 1/2 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class RepentantBlacksmith(Card):
    card_name = "Repentant Blacksmith"
