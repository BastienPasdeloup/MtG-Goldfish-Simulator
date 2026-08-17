"""Battering Ram — {2} Artifact Creature — Construct 1/1.
At the beginning of combat on your turn, it gains banding until end of combat.
Whenever it becomes blocked by a Wall, destroy that Wall at end of combat.

Both abilities concern blocking (banding matters only when blocked; the Wall
clause needs a blocking Wall). A goldfish has no blockers, so both are inert — a
fixed 1/1 artifact body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BatteringRam(Card):
    card_name = "Battering Ram"
