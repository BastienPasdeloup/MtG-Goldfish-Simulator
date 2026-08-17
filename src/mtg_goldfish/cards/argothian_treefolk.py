"""Argothian Treefolk — {3}{G}{G} Creature — Treefolk 3/5.

"Prevent all damage that would be dealt to this creature by artifact sources" is
inert in a goldfish (nothing deals damage to your creatures) — a fixed body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ArgothianTreefolk(Card):
    card_name = "Argothian Treefolk"
