"""Timber Wolves
{G} Creature — Wolf 1/1. Banding.

Banding is a combat-only ability with no effect in a solitaire goldfish.
Effectively a vanilla 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TimberWolves(Card):
    card_name = "Timber Wolves"
