"""Drudge Skeletons
{1}{B} Creature — Skeleton 1/1. {B}: Regenerate this creature.
Regeneration is a no-op with no destruction — a plain 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DrudgeSkeletons(Card):
    card_name = "Drudge Skeletons"
