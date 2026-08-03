"""Corpse Dance — {2}{B} Instant. Buyback {2}. Return the top creature card of
your graveyard to the battlefield with haste; exile it at the next end step.
(Buyback is offered as an alternate line that returns Corpse Dance to hand.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import reanimate_top_creature
from .base import Card, CardAction
from .registry import register

_BUYBACK = ManaCost(generic=2)


@register
class CorpseDance(Card):
    card_name = "Corpse Dance"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not any(c.is_creature for c in state.graveyard):
            return []
        acts = []

        def make(buyback: bool):
            total = ManaCost(generic=cost.generic + (_BUYBACK.generic if buyback else 0),
                             pips=cost.pips)

            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, total):
                    return None
                if card in st.stack:
                    st.stack.remove(card)
                if buyback:
                    st.hand.append(card)
                    st.emit("Corpse Dance: buyback — return to hand")
                else:
                    resolve_to_graveyard(st, card)
                return reanimate_top_creature(st, note=" (haste; exile at end step)")
            return fn

        if can_afford(state, cost):
            acts.append(CardAction("cast Corpse Dance", make(False)))
        total = ManaCost(generic=cost.generic + _BUYBACK.generic, pips=cost.pips)
        if can_afford(state, total):
            acts.append(CardAction("cast Corpse Dance (buyback {2})", make(True)))
        return acts
