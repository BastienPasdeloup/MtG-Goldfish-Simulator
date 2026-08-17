"""Yotian Soldier — {3} Artifact Creature — Soldier 1/4, Vigilance.

Vigilance is auto from the printed keyword; a fixed body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class YotianSoldier(Card):
    card_name = "Yotian Soldier"
