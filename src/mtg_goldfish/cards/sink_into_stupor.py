"""Sink into Stupor // Soporific Springs — Instant // Land.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SinkIntoStupor(Card):
    card_name = 'Sink into Stupor // Soporific Springs'
