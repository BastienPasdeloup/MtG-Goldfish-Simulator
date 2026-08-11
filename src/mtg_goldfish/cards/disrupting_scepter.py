"""Disrupting Scepter
{3} Artifact — {3}, {T}: Target player discards a card.
Aimed at an opponent's hand (none in a goldfish) — a {3} artifact with a no-op
ability."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DisruptingScepter(Card):
    card_name = "Disrupting Scepter"
