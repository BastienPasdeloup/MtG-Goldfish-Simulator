"""City of Traitors — Land.
{T}: Add {C}{C}. When you play another land, sacrifice this land.
Approximation: the sacrifice triggers on ANY other land entering (played or
fetched); strictly it only triggers on land drops."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class CityOfTraitors(Card):
    card_name = "City of Traitors"

    def mana_abilities(self, state):
        return [ManaAbility(amount=2, choices=("C",))]

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            state.emit("City of Traitors: another land entered — sacrifice")
            state.leaves_battlefield(perm, "graveyard")
