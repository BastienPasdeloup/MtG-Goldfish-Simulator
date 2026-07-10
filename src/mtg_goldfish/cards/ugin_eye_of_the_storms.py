"""Ugin, Eye of the Storms — {7} Legendary Planeswalker — Ugin.
Enters with 7 loyalty. One loyalty ability per turn (sorcery speed):
 +2: gain 3 life and draw a card;
  0: add {C}{C}{C} (to the pool, this phase).
The exile-on-cast triggers and the −11 ultimate target opponents' permanents
or free-cast piles that are out of scope — not modelled."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class UginEyeOfTheStorms(Card):
    card_name = "Ugin, Eye of the Storms"

    def on_etb(self, state, permanent):
        permanent.counters["loyalty"] = 7

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("loyalty_used"):
            return []

        def plus2(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return None
            p.turn_flags["loyalty_used"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 2
            st.life += 3
            st.emit(f"Ugin +2 (loyalty {p.counters['loyalty']}): gain 3 life, draw")
            st.draw(1)
            return None

        def zero(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return None
            p.turn_flags["loyalty_used"] = 1
            st.mana_pool.add("C", 3)
            st.emit("Ugin 0: add {C}{C}{C}")
            return None

        return [
            CardAction("Ugin: +2 gain 3 life, draw", plus2),
            CardAction("Ugin: 0 add {C}{C}{C}", zero),
        ]
