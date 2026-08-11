"""Paradox Engine — {5} Legendary Artifact.
Whenever you cast a spell, untap all nonland permanents you control.

A combo engine: each spell you cast untaps your mana rocks (and creatures), so the
search can chain casts. Casting Paradox Engine itself doesn't trigger it (it isn't
on the battlefield yet)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ParadoxEngine(Card):
    card_name = "Paradox Engine"

    def on_cast_other(self, state, perm, card):
        untapped = [p for p in state.battlefield if not p.is_land and p.tapped]
        for p in untapped:
            p.tapped = False
        if untapped:
            state.emit(f"Paradox Engine: untap {len(untapped)} nonland permanent(s)")
