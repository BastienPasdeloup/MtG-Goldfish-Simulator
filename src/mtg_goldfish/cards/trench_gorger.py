"""Trench Gorger — {6}{U}{U} 6/6 Trample. When it enters, you may search your
library for any number of land cards, exile them, then shuffle; its base power and
toughness each become the number of cards exiled this way.
Modelled as a branch: exile NO lands (stays 6/6) or ALL library lands (a huge
body but no library mana left) — the two extremes that matter in a goldfish."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class TrenchGorger(Card):
    card_name = "Trench Gorger"

    def dynamic_power(self, state, perm):
        n = perm.counters.get("gorger_size")
        return n if n is not None else None

    def dynamic_toughness(self, state, perm):
        n = perm.counters.get("gorger_size")
        return n if n is not None else None

    def on_etb(self, state, permanent):
        lands = state.search_library(lambda c: c.is_land)
        if not lands:
            return None

        def fn(st, take_all):
            if not take_all:
                st.emit("Trench Gorger: exile no lands (stays 6/6)")
                return None
            p = st.find_permanent(permanent.uid)
            n = 0
            for c in list(st.library):
                if c.is_land:
                    st.take_from_library(c)
                    st.exile.append(c)
                    n += 1
            st.shuffle_library()
            if p is not None:
                p.counters["gorger_size"] = n
            st.emit(f"Trench Gorger: exile {n} lands — base power/toughness {n}")
            return None

        return branch_over(state, [False, True], fn)
