"""Tawnos's Wand — {4} Artifact.
{2}, {T}: Target creature with power 2 or less can't be blocked this turn.

A goldfish has no blockers, so "can't be blocked" is fully inert (your attackers
are never blocked anyway). Registered as a fixed artifact — the sole ability
grants nothing observable here, so it is not offered as a search branch."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TawnossWand(Card):
    card_name = "Tawnos's Wand"
