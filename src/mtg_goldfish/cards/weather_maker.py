"""Weather Maker — {3} Artifact.
Landfall: put a charge counter on it. {T}: Add one mana of any color. The
charge-removal abilities ({C}{C}; 3 damage) are situational and not modelled;
its role here is a landfall-fed mana rock."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class WeatherMaker(Card):
    card_name = "Weather Maker"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]

    def other_etb_stack_items(self, state, perm, entering):
        if not entering.is_land:
            return []

        def resolve(st, uid=perm.uid, entering_uid=entering.uid):
            live = st.find_permanent(uid)
            new_perm = st.find_permanent(entering_uid)
            if live is None or new_perm is None:
                return None
            return live.impl.on_other_etb(st, live, new_perm)

        return [self.stack_ability(
            source_name=perm.name,
            label="Weather Maker: landfall",
            resolve=resolve,
            trigger_text=f"{entering.name} entered the battlefield",
            ability_text="Landfall — put a charge counter on Weather Maker",
        )]

    def on_other_etb(self, state, perm, entering):
        if entering.is_land:
            perm.counters["charge"] = perm.counters.get("charge", 0) + 1
