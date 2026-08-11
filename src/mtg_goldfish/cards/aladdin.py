"""Aladdin — {2}{R}{R} Creature — Human Rogue 1/1.
{1}{R}{R}, {T}: Gain control of target artifact for as long as you control this
creature.

Stealing control only matters against an opponent's artifact; you already control
your own, so the ability is inert. A 1/1 body that still enters."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Aladdin(Card):
    card_name = "Aladdin"
