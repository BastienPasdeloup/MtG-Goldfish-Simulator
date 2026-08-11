"""Cockatrice
{3}{G}{G} Creature — Cockatrice 2/4. Flying; destroys non-Wall creatures it blocks/is blocked by. The block-destroy is a defensive combat effect (no blockers in a goldfish) — a plain 2/4 flyer."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Cockatrice(Card):
    card_name = "Cockatrice"
