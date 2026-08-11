"""Sorceress Queen — {1}{B}{B} Creature — Human Wizard Sorcerer 1/1.
{T}: Target creature other than this creature has base power and toughness 0/2
until end of turn.

Shrinking a creature to 0/2 only matters against an opponent's creature; on your
own it's a downside, so the ability is inert. A 1/1 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class SorceressQueen(Card):
    card_name = "Sorceress Queen"
