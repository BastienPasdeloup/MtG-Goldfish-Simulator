"""Singing Tree — {3}{G} Creature — Plant 0/3.
{T}: Target attacking creature has base power 0 until end of turn.

Only weakens an ATTACKING creature (your own, in a goldfish) — never worth it — so
the ability is inert. A 0/3 wall-like body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class SingingTree(Card):
    card_name = "Singing Tree"
