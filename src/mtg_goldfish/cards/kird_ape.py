"""Kird Ape — {R} Creature — Ape 1/1.
This creature gets +1/+2 as long as you control a Forest.

A self-anthem via static_pt_bonus: +1/+2 to itself while you control a Forest."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class KirdApe(Card):
    card_name = "Kird Ape"

    def static_pt_bonus(self, state, source, perm):
        if perm.uid == source.uid and any(
                p.is_land and "forest" in p.type_line.lower() for p in state.battlefield):
            return (1, 2)
        return (0, 0)
