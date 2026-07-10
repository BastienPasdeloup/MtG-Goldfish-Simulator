"""Horizon Explorer — {2}{G} Creature — Insect Scout 2/4.
"Lands you control enter untapped" — modelled by untapping any land the
moment it enters (equivalent in a goldfish). Whenever you attack, create a
Lander token."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HorizonExplorer(Card):
    card_name = "Horizon Explorer"

    def on_other_etb_immediate(self, state, perm, entering):
        if "land" in entering.type_line.lower() and entering.tapped:
            entering.tapped = False
            state.emit(f"Horizon Explorer: {entering.name} enters untapped")

    def on_attack(self, state, perm):
        state.make_token("Lander", 0, 0, "Token Artifact — Lander")
        state.emit("Horizon Explorer: create a Lander token")
