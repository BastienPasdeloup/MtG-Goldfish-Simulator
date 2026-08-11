"""Camouflage
{G} Instant — randomizes how attackers are blocked.
A blocking modifier with no defenders in a goldfish — no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Camouflage(Card):
    card_name = "Camouflage"
