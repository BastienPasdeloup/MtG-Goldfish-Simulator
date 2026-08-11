"""Elvish Archers
{1}{G} Creature — Elf Archer 2/1. First strike (a plain 2/1 in a goldfish — no blockers)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ElvishArchers(Card):
    card_name = "Elvish Archers"
