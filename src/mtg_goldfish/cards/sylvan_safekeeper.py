"""Sylvan Safekeeper — {G} Creature — Human Wizard 1/1.
"Sacrifice a land: target creature you control gains shroud" — purely
protective (matters only against opponents' removal, which doesn't exist in a
goldfish). No beneficial use, so no activated ability is exposed; it plays as
a vanilla 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SylvanSafekeeper(Card):
    card_name = "Sylvan Safekeeper"
