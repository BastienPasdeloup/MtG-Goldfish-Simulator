"""Rock Hydra — {X}{R}{R} Creature — Hydra 0/0.
This creature enters with X +1/+1 counters on it.
For each 1 damage that would be dealt to this creature, if it has a +1/+1 counter,
remove a +1/+1 counter and prevent that 1 damage.
{R}: Prevent the next 1 damage that would be dealt to this creature this turn.
{R}{R}{R}: Put a +1/+1 counter on this creature. Activate only during your upkeep.

Enters as an X/X (X +1/+1 counters — one cast branch per affordable X). The
{R}{R}{R} pump (add a +1/+1 counter) is offered from the battlefield; the
damage-prevention-by-counter-removal riders are a simplification not modelled
(the body / counters are)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class RockHydra(Card):
    card_name = "Rock Hydra"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_battlefield)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("R", 1), ("R", 1)))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    return resolve_to_battlefield(st, card, marks={"+1/+1": xx})
                return fn

            acts.append(CardAction(f"cast Rock Hydra (X={x}) → {x}/{x}", make(x)))
        return acts

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1), ("R", 1), ("R", 1)))
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            p = st.find_permanent(perm.uid)
            if p is not None:
                p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
                st.emit("Rock Hydra: +1/+1 counter")
            return None

        return [CardAction.activated(
            "Rock Hydra: {R}{R}{R} — put a +1/+1 counter",
            pay, resolve, source_name="Rock Hydra",
            ability_text="Put a +1/+1 counter on this creature")]
