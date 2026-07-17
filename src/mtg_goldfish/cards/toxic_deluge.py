"""Toxic Deluge — {2}{B} Sorcery. Pay X life as an additional cost; all creatures
get -X/-X until end of turn. In a goldfish this only wipes your own board, so a
single representative X (enough to clear the board) is offered rather than
branching over every X."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ToxicDeluge(Card):
    card_name = "Toxic Deluge"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        cost = self.cast_cost(state)
        creatures = [p for p in state.battlefield if p.is_creature_now]
        if not creatures or not can_afford(state, cost):
            return []
        x = min(max(state.effective_toughness(p) for p in creatures), state.life - 1)
        if x <= 0:
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or st.life <= x or not begin_cast(st, card, cost):
                return None
            from ..engine.actions import resolve_to_graveyard
            resolve_to_graveyard(st, card)
            st.life -= x
            for p in list(st.battlefield):
                if p.is_creature_now:
                    p.temp_power -= x
                    p.temp_toughness -= x
            st.emit(f"Toxic Deluge: pay {x} life, all creatures get -{x}/-{x}")
            st.check_deaths()
            return None

        return [CardAction(f"cast Toxic Deluge (X={x})", fn)]
