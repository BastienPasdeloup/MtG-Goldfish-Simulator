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

    def enters_with_counters(self, state):
        # Starting loyalty is a replacement effect: the counters are on the
        # planeswalker from the moment it enters; nothing goes on the stack.
        return {"loyalty": 7}

    def battlefield_actions(self, state, perm):
        if perm.turn_flags.get("loyalty_used"):
            return []

        def pay_plus2(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return False
            p.turn_flags["loyalty_used"] = 1
            p.counters["loyalty"] = p.counters.get("loyalty", 0) + 2
            return True

        def resolve_plus2(st):
            p = st.find_permanent(perm.uid)
            loyalty = p.counters.get("loyalty", 0) if p is not None else 0
            st.gain_life(3)
            st.emit(f"Ugin +2 (loyalty {loyalty}): gain 3 life, draw")
            st.draw(1)
            return None

        def pay_zero(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.turn_flags.get("loyalty_used"):
                return False
            p.turn_flags["loyalty_used"] = 1
            return True

        def resolve_zero(st):
            st.mana_pool.add("C", 3)
            st.emit("Ugin 0: add {C}{C}{C}")
            return None

        return [
            CardAction.activated(
                "Ugin: +2 gain 3 life, draw",
                pay_plus2,
                resolve_plus2,
                source_name="Ugin, Eye of the Storms",
                ability_text="Gain 3 life and draw a card",
            ),
            CardAction.activated(
                "Ugin: 0 add {C}{C}{C}",
                pay_zero,
                resolve_zero,
                source_name="Ugin, Eye of the Storms",
                ability_text="Add {C}{C}{C}",
            ),
        ]
