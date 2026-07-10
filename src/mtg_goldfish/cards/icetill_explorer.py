"""Icetill Explorer — {2}{G}{G} Creature — Insect Scout 2/4.
You may play an additional land on each of your turns. You may play lands
from your graveyard. Landfall: mill a card."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IcetillExplorer(Card):
    card_name = "Icetill Explorer"

    grants_gy_land_plays = True

    def extra_land_drops(self, state, perm):
        return 1

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            state.mill(1)
