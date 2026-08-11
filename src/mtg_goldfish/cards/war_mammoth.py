"""War Mammoth — 3/3 Elephant, Trample.

Printed keywords are auto (Defender can't attack, others inert with no blockers).
Effectively a fixed body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WarMammoth(Card):
    card_name = "War Mammoth"
