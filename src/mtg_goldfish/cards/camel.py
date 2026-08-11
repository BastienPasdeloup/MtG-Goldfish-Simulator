"""Camel — {W} Creature — Camel 0/1. Banding.
As long as this creature is attacking, prevent all damage Deserts would deal to it
and to creatures banded with it.

Banding and the Desert-damage prevention are combat-only interactions inert in a
solitaire goldfish. A 0/1 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Camel(Card):
    card_name = "Camel"
