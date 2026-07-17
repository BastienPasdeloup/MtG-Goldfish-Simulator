"""Consult the Star Charts — {1}{U} Instant, Kicker {1}{U}. Look at the top X
cards, where X is the number of lands you control; put one (two if kicked) into
your hand and the rest on the bottom in a random order."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import dig_choose
from .base import Card, CardAction
from .registry import register


@register
class ConsultTheStarCharts(Card):
    card_name = "Consult the Star Charts"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        base = self.cast_cost(state)  # {1}{U}
        kicked = ManaCost(generic=base.generic + 1, pips=(("U", 2),))
        lands = state.lands_in_play()

        def make(cost, keep, tag):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost, tag=tag):
                    return None
                resolve_to_graveyard(st, card)
                return dig_choose(st, st.lands_in_play(), keep, rest="bottom",
                                  source="Consult the Star Charts")
            return fn

        acts = []
        if lands and can_afford(state, base):
            acts.append(CardAction("cast Consult the Star Charts (keep 1)",
                                   make(base, 1, "unkicked")))
        if lands and can_afford(state, kicked):
            acts.append(CardAction("cast Consult the Star Charts (kicked, keep 2)",
                                   make(kicked, 2, "kicked")))
        return acts
