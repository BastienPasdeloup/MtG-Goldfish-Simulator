"""Obsianus Golem
{6} Artifact Creature — Golem 4/6. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ObsianusGolem(Card):
    card_name = "Obsianus Golem"
