"""Eye of Ugin — Legendary Land.
Produces no mana. Colorless Eldrazi spells cost {2} less (honoured by
Emrakul / Kozilek's Command / Sowing Mycospawn via `eldrazi_discount`).
{7}, {T}: search your library for a colorless creature card, put it into
your hand, then shuffle (branch per target)."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


def eldrazi_discount(state) -> int:
    """{2} per Eye of Ugin you control, for colorless Eldrazi spells."""
    return 2 * sum(1 for p in state.battlefield if p.name == "Eye of Ugin")


@register
class EyeOfUgin(Card):
    card_name = "Eye of Ugin"

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=7)
        if perm.tapped or not can_afford(state, cost):
            return []

        def make(name):
            def fn(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost):
                    return None
                p.tapped = True
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                st.hand.append(card)
                st.emit(f"Eye of Ugin: search {name} to hand — shuffle")
                return None
            return fn

        targets = state.search_library(lambda c: c.is_creature and not c.colors)
        return [CardAction(f"Eye of Ugin: search {t.name}", make(t.name)) for t in targets]
