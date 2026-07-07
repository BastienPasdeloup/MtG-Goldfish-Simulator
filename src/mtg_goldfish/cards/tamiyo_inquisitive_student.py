"""Tamiyo, Inquisitive Student // Tamiyo, Seasoned Scholar — Legendary Creature — Moonfolk Wizard // Legendary Planeswalker — Tamiyo.

Best-effort implementation: modelled as being cast/entering and counting toward
board state and spell tallies; its special rules text is not simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TamiyoInquisitiveStudent(Card):
    card_name = 'Tamiyo, Inquisitive Student // Tamiyo, Seasoned Scholar'
