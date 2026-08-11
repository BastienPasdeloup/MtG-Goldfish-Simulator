"""Black Vise — {1} Artifact.
As this enters, choose an opponent; at their upkeep it damages them by (cards in
hand − 4). With no opponent in a solitaire goldfish it never deals damage — a
{1} artifact (permanent / artifact count)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BlackVise(Card):
    card_name = "Black Vise"
