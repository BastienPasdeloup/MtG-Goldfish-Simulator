"""Flow State — {1}{U} Sorcery. Look at the top three cards; put one into your
hand and the rest on the bottom. If there is an instant AND a sorcery in your
graveyard, put two into your hand instead."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class FlowState(Card):
    card_name = "Flow State"

    def on_resolve(self, state):
        gy = state.graveyard
        boosted = any(c.is_instant for c in gy) and any(c.is_sorcery for c in gy)
        keep = 2 if boosted else 1
        return dig_choose(state, 3, keep, rest="bottom", source="Flow State")
