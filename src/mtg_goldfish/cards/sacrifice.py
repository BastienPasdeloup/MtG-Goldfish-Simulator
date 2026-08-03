"""Sacrifice — {B} Instant. As an additional cost, sacrifice a creature. Add an
amount of {B} equal to the sacrificed creature's mana value (a ritual — branch
over which creature to sacrifice)."""
from __future__ import annotations

from ._common import mv
from .base import Card, CardAction
from .registry import register


@register
class Sacrifice(Card):
    card_name = "Sacrifice"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        acts, seen = [], set()
        for c in state.battlefield:
            if not c.is_creature_now or c.name in seen:
                continue
            seen.add(c.name)

            def make(uid=c.uid, name=c.name):
                def fn(st):
                    card = next((x for x in st.hand if x.name == self.card_name), None)
                    victim = st.find_permanent(uid)
                    if card is None or victim is None or not begin_cast(st, card, cost):
                        return None
                    resolve_to_graveyard(st, card)
                    amount = mv(victim.card)
                    st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
                    st.mana_pool.add("B", amount)
                    st.emit(f"Sacrifice: sacrifice {name} — add {{B}}×{amount}")
                    return None
                return fn

            acts.append(CardAction(f"cast Sacrifice (sac {c.name})", make()))
        return acts
