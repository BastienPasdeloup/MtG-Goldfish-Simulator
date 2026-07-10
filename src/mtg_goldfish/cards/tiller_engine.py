"""Tiller Engine — {2} Artifact Creature — Construct 1/3.
Whenever a land you control enters tapped, you may untap it (the opponent-tap
mode is irrelevant). Modelled as: untap any land that enters tapped."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TillerEngine(Card):
    card_name = "Tiller Engine"

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower() and entering.tapped:
            entering.tapped = False
            state.emit(f"Tiller Engine: untap {entering.name}")
