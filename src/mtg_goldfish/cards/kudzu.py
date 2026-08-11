"""Kudzu — {1}{G}{G} Enchantment — Aura. Enchant land.
When enchanted land becomes tapped, destroy it. That land's controller may attach
this Aura to a land of their choice.

Enchant one of your lands; the next time that land is tapped for mana it is
destroyed (via the land-tap broadcast). The re-attach ("move Kudzu to another
land") is simplified — the Aura is destroyed along with its host."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Kudzu(Card):
    card_name = "Kudzu"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{G}{G}",
                                    pred=lambda p: p.is_land)

    def on_land_tapped_for_mana(self, state, perm, land, color):
        if perm.attached_to == land.uid:
            state.emit(f"Kudzu: {land.name} was tapped — destroy it")
            state.leaves_battlefield(land, "graveyard", reason="destroy")
        return None
