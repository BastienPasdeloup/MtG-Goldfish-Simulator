"""City of Traitors — Land.
{T}: Add {C}{C}. When you play another land, sacrifice this land.
Modelled exactly: it triggers only when another land is actually played, not
when a land is put onto the battlefield by an effect."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class CityOfTraitors(Card):
    card_name = "City of Traitors"

    def mana_abilities(self, state):
        return [ManaAbility(amount=2, choices=("C",))]

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.is_land or not entering.turn_flags.get("played_as_land"):
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="City of Traitors: sacrifice trigger",
            resolve=resolve,
            trigger_text=f"{entering.name} was played as a land",
            ability_text="When you play another land, sacrifice City of Traitors",
        )]

    def on_other_etb(self, state, perm, entering):
        if entering.is_land and entering.turn_flags.get("played_as_land"):
            state.emit("City of Traitors: another land was played — sacrifice")
            state.leaves_battlefield(perm, "graveyard")
