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

    def other_etb_stack_items(self, state, perm, entering):
        if "land" not in entering.type_line.lower():
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Icetill Explorer: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — mill a card",
        )]

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            state.mill(1)
