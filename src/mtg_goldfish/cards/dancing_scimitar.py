"""Dancing Scimitar
{4} Artifact Creature — Spirit 1/5. Flying.

Flying is auto from the keyword; otherwise a vanilla 1/5 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DancingScimitar(Card):
    card_name = "Dancing Scimitar"
