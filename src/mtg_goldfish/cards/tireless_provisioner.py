"""Tireless Provisioner — {2}{G} Creature — Elf Scout 3/2.
Landfall: create a Food token or a Treasure token. Approximation: always
makes a Treasure (mana ramp is the useful mode in this deck) — landfall
triggers fire deep inside land resolution and can't branch the search."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TirelessProvisioner(Card):
    card_name = "Tireless Provisioner"

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            state.make_token("Treasure", 0, 0, "Token Artifact — Treasure")
            state.emit("Tireless Provisioner: landfall — Treasure token")
