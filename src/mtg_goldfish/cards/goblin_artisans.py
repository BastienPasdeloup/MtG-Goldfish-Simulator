"""Goblin Artisans — {R} Creature — Goblin Artificer 1/1.
{T}: Flip a coin. If you win the flip, draw a card. If you lose the flip, counter
target artifact spell you control (that isn't targeted by another Goblin Artisans).

The coin flip is explored as two branches: win → draw a card; lose → counter one
of your own artifact spells, but spells resolve atomically here so there is none on
the stack to counter (the lose branch does nothing)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class GoblinArtisans(Card):
    card_name = "Goblin Artisans"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            return True

        def resolve(st):
            def fn(s2, outcome):
                if outcome == "win":
                    s2.draw(1)
                    s2.emit("Goblin Artisans: win the flip — draw a card")
                else:
                    s2.emit("Goblin Artisans: lose the flip — no artifact spell on the stack to counter")
                return None

            return branch_over(st, ["win", "lose"], fn)

        return [CardAction.activated(
            "Goblin Artisans: {T} — flip a coin (win: draw a card)",
            pay, resolve, source_name="Goblin Artisans",
            ability_text="Flip a coin: win draws a card")]
