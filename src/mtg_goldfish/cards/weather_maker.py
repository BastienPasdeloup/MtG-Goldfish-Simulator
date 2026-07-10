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

    def on_other_etb(self, state, perm, entering):
        if "land" in entering.type_line.lower():
            perm.counters["charge"] = perm.counters.get("charge", 0) + 1
