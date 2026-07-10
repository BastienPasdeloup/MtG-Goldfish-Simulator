"""Kozilek's Command — {X}{C}{C} Kindred Instant — Eldrazi.
Choose two modes. In a goldfish the useful, self-contained modes are:
 • create X 0/1 Eldrazi Spawn, and
 • scry X then draw a card.
Modelled as always choosing those two (the exile modes need opponents/enemy
graveyards). Branch over affordable X. Cost reduced by Eye of Ugin (colorless
Eldrazi spell)."""
from __future__ import annotations

from ..engine.actions import available_mana_sources, begin_cast, resolve_to_graveyard
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register
from .eye_of_ugin import eldrazi_discount


@register
class KozileksCommand(Card):
    card_name = "Kozilek's Command"

    def cast_actions(self, state):
        disc = eldrazi_discount(state)
        max_mana = len(available_mana_sources(state)) + state.mana_pool.total()
        acts = []
        for x in range(0, max(0, max_mana) + 1):
            generic = max(0, x - disc)
            cost = ManaCost(generic=generic, pips=(("C", 2),))

            def make(xx=x, xc=cost):
                def fn(st):
                    card = next((c for c in st.hand if c.name == self.card_name), None)
                    if card is None or not begin_cast(st, card, xc):
                        return None
                    resolve_to_graveyard(st, card)
                    for _ in range(xx):
                        st.make_token("Eldrazi Spawn", 0, 1, "Token Creature — Eldrazi Spawn")
                    st.draw(1)
                    st.emit(f"Kozilek's Command (X={xx}): {xx} Spawn, draw a card")
                    return None
                return fn

            acts.append(CardAction(f"cast Kozilek's Command (X={x}): Spawn + draw", make()))
        return acts
