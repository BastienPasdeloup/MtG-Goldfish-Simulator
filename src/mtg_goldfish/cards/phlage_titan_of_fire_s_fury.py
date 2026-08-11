"""Phlage, Titan of Fire's Fury — {1}{R}{W} Legendary Creature 6/6.
When it enters, sacrifice it unless it escaped. Whenever it enters or attacks:
3 damage to any target (the opponent — deterministic in a trigger) and you gain
3 life. Escape — {R}{R}{W}{W}, exile five other cards from your graveyard
(exiled cards chosen deterministically: first five — approximation)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register

_ESCAPE = ManaCost(pips=(("R", 2), ("W", 2)))


def _fury(state, perm) -> None:
    state.damage_opponent(3)  # noncombat -> amplifiers apply
    state.gain_life(3)
    state.emit(f"Phlage: 3 damage to opponent ({state.opponent_life}), gain 3 life ({state.life})")


@register
class Phlage(Card):
    card_name = "Phlage, Titan of Fire's Fury"

    def on_etb(self, state, permanent):
        _fury(state, permanent)
        if not permanent.counters.get("escaped"):
            state.emit("Phlage: sacrificed (did not escape)")
            state.leaves_battlefield(permanent, "graveyard")
        return None

    def on_attack(self, state, perm):
        _fury(state, perm)

    def graveyard_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_battlefield

        others = [c for c in state.graveyard if c.name != self.card_name]
        if len(others) < 5 or not can_afford(state, _ESCAPE):
            return []

        def fn(st):
            card = next((c for c in st.graveyard if c.name == self.card_name), None)
            if card is None:
                return None
            pool = [c for c in st.graveyard if c.name != self.card_name][:5]
            if len(pool) < 5:
                return None
            for c in pool:
                st.graveyard.remove(c)
                st.exile.append(c)
            st.emit(f"escape Phlage: exile {', '.join(c.name for c in pool)}")
            if not begin_cast(st, card, _ESCAPE, zone=st.graveyard, tag="escape"):
                return None
            return resolve_to_battlefield(st, card, marks={"escaped": 1}) or None

        return [CardAction("cast Phlage from graveyard (escape)", fn)]
