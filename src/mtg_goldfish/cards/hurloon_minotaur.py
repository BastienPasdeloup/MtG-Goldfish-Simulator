"""Hurloon Minotaur
{1}{R}{R} Creature — Minotaur 2/3. Vanilla."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HurloonMinotaur(Card):
    card_name = "Hurloon Minotaur"
