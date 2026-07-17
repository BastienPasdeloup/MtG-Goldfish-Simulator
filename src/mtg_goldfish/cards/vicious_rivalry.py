"""Vicious Rivalry — {2}{B}{G} Sorcery. Pay X life as an additional cost; destroy
all artifacts and creatures with mana value X or less. In a goldfish this only
hits your own permanents, so a single representative X (enough to clear the
board) is offered rather than branching over every X."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ViciousRivalry(Card):
    card_name = "Vicious Rivalry"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        hittable = [p for p in state.battlefield
                    if p.is_creature_now or "artifact" in p.type_line.lower()]
        if not hittable or not can_afford(state, cost):
            return []
        x = min(max(int(p.card.cmc) for p in hittable), state.life - 1)
        if x < 0:
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or st.life <= x or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            st.life -= x
            for p in list(st.battlefield):
                if (p.is_creature_now or "artifact" in p.type_line.lower()) and int(p.card.cmc) <= x:
                    st.emit(f"Vicious Rivalry: destroy {p.name}")
                    st.leaves_battlefield(p, "graveyard", reason="destroy")
            st.emit(f"Vicious Rivalry: pay {x} life, destroy mv≤{x}")
            return None

        return [CardAction(f"cast Vicious Rivalry (X={x})", fn)]
