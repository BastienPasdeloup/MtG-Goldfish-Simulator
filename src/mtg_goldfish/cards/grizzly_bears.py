"""Grizzly Bears
{1}{G} Creature — Bear 2/2. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GrizzlyBears(Card):
    card_name = "Grizzly Bears"
