"""Beast Within — {2}{G} Instant.
Destroy target permanent; its controller creates a 3/3 Beast.
In a solitaire game the only legal targets are your own permanents (plus the
phantom opponent has none), so it's almost never useful — but it IS castable
(e.g. to trade a useless permanent for a 3/3 body). Branch over your own
nonland permanents; you get the 3/3 Beast."""
from __future__ import annotations

from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard
from .base import Card, CardAction
from .registry import register


@register
class BeastWithin(Card):
    card_name = "Beast Within"

    def cast_actions(self, state):
        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        targets = {}
        for p in state.battlefield:
            if not p.is_commander and p.name not in targets:
                targets[p.name] = p.uid

        def make(uid, name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                target = st.find_permanent(uid)
                if card is None or target is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.emit(f"Beast Within: destroy {target.name}")
                st.leaves_battlefield(target, "graveyard")
                st.make_token("Beast", 3, 3, "Token Creature — Beast")
                return None
            return fn

        return [CardAction(f"cast Beast Within → {name}", make(uid, name))
                for name, uid in targets.items()]
