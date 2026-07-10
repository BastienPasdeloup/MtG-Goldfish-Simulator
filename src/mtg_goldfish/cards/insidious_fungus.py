"""Insidious Fungus — {G} Creature — Fungus 1/2.
{2}, Sacrifice: draw a card, then you may put a land card from your hand onto
the battlefield tapped (branch per distinct land, plus keeping it in hand).
The destroy-artifact/enchantment modes only hit your own permanents in a
goldfish and are not modelled."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class InsidiousFungus(Card):
    card_name = "Insidious Fungus"

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            st.leaves_battlefield(p, "graveyard")
            return True

        def resolve(st):
            st.emit("Insidious Fungus: sacrifice — draw a card")
            st.draw(1)
            lands = sorted({c.name for c in st.hand if c.is_land})
            if not lands:
                return None
            out = []
            for name in lands + [None]:
                b = st.clone()
                if name is not None:
                    card = next(c for c in b.hand if c.name == name)
                    b.hand.remove(card)
                    enter_battlefield(
                        b,
                        card,
                        tapped=True,
                        announce=f"Insidious Fungus: put {name} onto the battlefield tapped",
                    )
                b.check_deaths()
                out.append(b)
            return out

        return [CardAction.activated(
            "Insidious Fungus: {2}, sac — draw, maybe a land",
            pay,
            resolve,
            source_name="Insidious Fungus",
            ability_text="Draw a card, then you may put a land card from your hand onto the battlefield tapped",
        )]
