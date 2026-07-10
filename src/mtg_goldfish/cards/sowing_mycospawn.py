"""Sowing Mycospawn — {3}{G} Creature — Eldrazi Fungus 3/3. Devoid.
Kicker {1}{C}. Cast trigger: search your library for a land card, put it onto
the battlefield, then shuffle (branch per land). The kicked "exile a land"
mode is opponent-facing — not modelled; we cast unkicked. Eye of Ugin reduces
the cost (colorless Eldrazi spell)."""
from __future__ import annotations

from ..engine.actions import begin_cast, can_afford
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register
from .eye_of_ugin import eldrazi_discount


@register
class SowingMycospawn(Card):
    card_name = "Sowing Mycospawn"

    def cast_cost(self, state):
        base = self.mana_cost
        return ManaCost(generic=max(0, base.generic - eldrazi_discount(state)),
                        pips=base.pips)

    def cast_actions(self, state):
        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        targets = state.search_library(lambda c: c.is_land)

        def make(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                # Cast trigger resolves first (search a land), then the body.
                land = next((c for c in st.library if c.name == name), None)
                if land is not None:
                    st.take_from_library(land)
                    st.shuffle_library()
                    st.put_on_battlefield(land)
                    st.emit(f"Sowing Mycospawn: {name} onto the battlefield — shuffle")
                from ..engine.actions import resolve_to_battlefield
                return resolve_to_battlefield(st, card) or None
            return fn

        # Also allow casting with no land left to find.
        acts = [CardAction(f"cast Sowing Mycospawn → fetch {t.name}", make(t.name))
                for t in targets]
        return acts
