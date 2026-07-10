"""Ba Sing Se — Land.
Enters tapped unless you control a basic land. {T}: Add {G}.
Approximation: the earthbend ability (land becomes a 0/0 creature with two
+1/+1 counters) is not modelled — attacking with lands is marginal here."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class BaSingSe(Card):
    card_name = "Ba Sing Se"

    def etb_tapped(self, state):
        return not any(
            "basic" in p.type_line.lower() and "land" in p.type_line.lower()
            for p in state.battlefield
        )

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
