"""Stone-Throwing Devils
{B} Creature — Devil 1/1. First strike.

First strike is inert with no blockers. A 1/1 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class StoneThrowingDevils(Card):
    card_name = "Stone-Throwing Devils"
