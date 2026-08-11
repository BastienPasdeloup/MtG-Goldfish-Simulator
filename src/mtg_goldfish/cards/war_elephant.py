"""War Elephant
{3}{W} Creature — Elephant 2/2. Trample, banding.

Trample is auto; banding is a combat-only ability inert in a solitaire goldfish.
A 2/2 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class WarElephant(Card):
    card_name = "War Elephant"
