"""Ironroot Treefolk
{4}{G} Creature — Treefolk 3/5. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IronrootTreefolk(Card):
    card_name = "Ironroot Treefolk"
