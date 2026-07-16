"""Moonshadow — {B} Creature 7/7, menace.
Enters with six -1/-1 counters; whenever one or more permanent cards are put into
your graveyard while it has a -1/-1 counter, remove a -1/-1 counter.
Modelled via dynamic P/T: it enters as a net 1/1 and grows toward 7/7 as
permanent cards fill your graveyard (baseline captured at ETB)."""
from __future__ import annotations

from .base import Card
from .registry import register


def _permanent_cards_in_gy(state) -> int:
    return sum(1 for c in state.graveyard if c.is_permanent)


@register
class Moonshadow(Card):
    card_name = "Moonshadow"

    def on_etb(self, state, permanent):
        permanent.counters["_gy_baseline"] = _permanent_cards_in_gy(state)

    def _remaining_neg(self, state, perm):
        base = perm.counters.get("_gy_baseline", 0)
        removed = max(0, _permanent_cards_in_gy(state) - base)
        return max(0, 6 - removed)

    def dynamic_power(self, state, perm):
        return 7 - self._remaining_neg(state, perm)

    def dynamic_toughness(self, state, perm):
        return 7 - self._remaining_neg(state, perm)
