"""Phantom Monster
{3}{U} Creature — Illusion 3/3. Flying.

Flying is auto from the keyword; otherwise a vanilla 3/3 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PhantomMonster(Card):
    card_name = "Phantom Monster"
