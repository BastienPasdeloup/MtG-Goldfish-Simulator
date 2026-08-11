"""Craw Wurm
{4}{G}{G} Creature — Wurm 6/4. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CrawWurm(Card):
    card_name = "Craw Wurm"
