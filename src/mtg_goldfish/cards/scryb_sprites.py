"""Scryb Sprites
{G} Creature — Faerie 1/1. Flying.

Flying is auto from the keyword; otherwise a vanilla 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ScrybSprites(Card):
    card_name = "Scryb Sprites"
