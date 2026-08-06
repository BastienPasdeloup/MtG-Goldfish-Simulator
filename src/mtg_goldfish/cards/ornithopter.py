"""Ornithopter — {0} Artifact Creature — Thopter 0/2.
Flying only; the engine reads the keyword from the card data, so no extra
behaviour is needed (this file just marks the card as implemented)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Ornithopter(Card):
    card_name = "Ornithopter"
