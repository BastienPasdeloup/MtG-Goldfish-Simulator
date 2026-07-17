"""Tasigur, the Golden Fang — {5}{B} Legendary Creature 4/5. Delve.
Delve reduces the generic cost by exiling graveyard cards; modelled here as a
cost reduction of up to five (the graveyard cards are NOT exiled — a benign
goldfish simplification that keeps the tempo without the downside).
{2}{G/U}{G/U}: Mill two cards, then return a nonland card of an opponent's choice
from your graveyard to your hand — approximated by returning your lowest-mana-
value nonland card (the least useful, as an opponent would choose)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class TasigurTheGoldenFang(Card):
    card_name = "Tasigur, the Golden Fang"

    def cast_cost(self, state):
        base = self.mana_cost  # {5}{B}
        reduce = min(len(state.graveyard), 5)
        return ManaCost(generic=max(0, base.generic - reduce), pips=base.pips)

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2, pips=(("G", 1), ("U", 1)))
        nonland = [c for c in state.graveyard if not c.is_land]
        if not nonland or not can_afford(state, cost):
            return []

        def pay(st):
            if not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            st.mill(2)
            pool = [c for c in st.graveyard if not c.is_land]
            if pool:
                worst = min(pool, key=lambda c: c.cmc)
                st.leave_graveyard(worst)
                st.hand.append(worst)
                st.emit(f"Tasigur: mill 2, return {worst.name} to hand")
            else:
                st.emit("Tasigur: mill 2, no nonland card to return")
            return None

        return [CardAction.activated(
            "Tasigur: {2}{G/U}{G/U} — mill 2, return a nonland card",
            pay, resolve,
            source_name="Tasigur, the Golden Fang",
            ability_text="Mill two, return a nonland card of an opponent's choice")]
