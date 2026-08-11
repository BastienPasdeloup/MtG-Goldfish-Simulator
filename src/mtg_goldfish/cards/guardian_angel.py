"""Guardian Angel — {X}{W} Instant.
Prevent the next X damage that would be dealt to any target this turn. Until end
of turn, you may pay {1} any time you could cast an instant. If you do, prevent
the next 1 damage that would be dealt to that permanent or player this turn.

Modelled as a prevention shield of X for yourself (one branch per affordable X).
The optional pay-{1}-for-more rider is not modelled (marginal here)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class GuardianAngel(Card):
    card_name = "Guardian Angel"

    def cast_actions(self, state):
        from ..engine.actions import (available_mana_sources, begin_cast,
                                       can_afford, resolve_to_graveyard)

        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(1, max(0, max_mana) + 1):
            cost = ManaCost(generic=x, pips=(("W", 1),))
            if not can_afford(state, cost):
                continue

            def make(xx, c=cost):
                def fn(st):
                    card = next((k for k in st.hand if k.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, c):
                        return None
                    resolve_to_graveyard(st, card)
                    st.prevent_shields.append((xx, None))
                    st.emit(f"Guardian Angel: prevent next {xx} damage to you this turn")
                    return None
                return fn

            acts.append(CardAction(f"cast Guardian Angel (X={x})", make(x)))
        return acts
