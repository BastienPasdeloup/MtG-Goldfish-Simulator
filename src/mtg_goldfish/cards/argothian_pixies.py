"""Argothian Pixies — {1}{G} Creature — Faerie 2/1.

"Can't be blocked by artifact creatures" and "prevent all damage dealt by
artifact creatures" are inert in a goldfish (no opposing blockers/creatures) —
a fixed body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ArgothianPixies(Card):
    card_name = "Argothian Pixies"
