"""Ankh of Mishra — {2} Artifact.
Whenever a land enters, this artifact deals 2 damage to that land's controller.

Symmetric in a solitaire goldfish: every land YOU play (or that enters) deals 2
damage to you — a real downside the search weighs."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AnkhOfMishra(Card):
    card_name = "Ankh of Mishra"

    def on_other_etb(self, state, perm, entering):
        if entering.is_land:
            state.emit(f"Ankh of Mishra: {entering.name} entered — deals 2 damage to you")
            state.damage_self(2)
