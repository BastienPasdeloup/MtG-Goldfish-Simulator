"""Sacrifice — {B} Instant. As an additional cost, sacrifice a creature. Add an
amount of {B} equal to the sacrificed creature's mana value (a ritual — branch
over which creature to sacrifice). The ritual also lives in `on_resolve` so it
works when cast from EXILE / graveyard (Hoarding Broodlord, Yawgmoth's Will)."""
from __future__ import annotations

from ._common import branch_over, mv
from .base import Card, CardAction
from .registry import register


def _sacrifice(st, uid, name):
    victim = st.find_permanent(uid)
    if victim is None:
        return None
    amount = mv(victim.card)
    st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
    st.mana_pool.add("B", amount)
    st.emit(f"Sacrifice: sacrifice {name} — add {{B}}×{amount}")
    return None


@register
class Sacrifice(Card):
    card_name = "Sacrifice"

    def on_resolve(self, state):
        vics, seen = [], set()
        for c in state.battlefield:
            if c.is_creature_now and c.name not in seen:
                seen.add(c.name)
                vics.append((c.uid, c.name))
        if not vics:
            return None
        return branch_over(state, vics, lambda st, v: _sacrifice(st, v[0], v[1]))

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
                    if card is None or st.find_permanent(uid) is None or not begin_cast(st, card, cost):
                        return None
                    resolve_to_graveyard(st, card)
                    return _sacrifice(st, uid, name)
                return fn

            acts.append(CardAction(f"cast Sacrifice (sac {c.name})", make()))
        return acts
