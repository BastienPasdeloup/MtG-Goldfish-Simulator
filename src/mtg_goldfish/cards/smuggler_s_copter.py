"""Smuggler's Copter — {2} Artifact — Vehicle 3/3, flying, crew 1.
A Vehicle is not a creature until crewed; crewing (and therefore its
attack/block loot trigger) is not modelled in this goldfish — the permanent
enters and counts as an artifact exactly."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SmugglersCopter(Card):
    card_name = "Smuggler's Copter"
