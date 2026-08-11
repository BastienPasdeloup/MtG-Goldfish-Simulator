"""Lodestone Bauble — {0} Artifact.
{1}, {T}, Sacrifice this artifact: Put up to four target basic land cards from a
player's graveyard on top of their library in any order. That player draws a card
at the beginning of the next turn's upkeep.

Targeting yourself: any basic lands in your graveyard go back on top of your
library, then you draw at your next upkeep. In this (near-mono-U, mostly nonbasic)
deck the recursion rarely applies, so the modelled value is the delayed draw."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class LodestoneBauble(Card):
    card_name = "Lodestone Bauble"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            # Put up to four of your basic lands from the graveyard on top of the
            # library (helps you redraw them), then draw at the next upkeep.
            basics = [c for c in st.graveyard
                      if c.is_land and "basic" in c.type_line.lower()][:4]
            for c in basics:
                st.graveyard.remove(c)
                st.library.insert(0, c)
                st.mark_known_in_library(c)
            if basics:
                st.emit(f"Lodestone Bauble: put {len(basics)} basic(s) on top of library")
            st.pending_upkeep_draws += 1
            st.emit("Lodestone Bauble: draw a card at the next upkeep")
            return None

        return [CardAction.activated(
            "Lodestone Bauble: {1}, {T}, sacrifice — recycle basics + draw next upkeep",
            pay, resolve, source_name="Lodestone Bauble",
            ability_text="Recycle basic lands; draw a card next upkeep")]
