"""Gray Ogre
{2}{R} Creature — Ogre 2/2. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GrayOgre(Card):
    card_name = "Gray Ogre"
