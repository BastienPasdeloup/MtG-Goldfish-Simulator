"""Verduran Enchantress — {1}{G}{G} Creature — Human Druid 0/2.
Whenever you cast an enchantment spell, you may draw a card.

On each enchantment spell you cast, a branch: draw a card, or decline (there is no
cost, so the search will normally draw)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class VerduranEnchantress(Card):
    card_name = "Verduran Enchantress"

    def on_cast_other(self, state, perm, card):
        if "enchantment" not in (card.type_line or "").lower():
            return None

        def fn(st, opt):
            if opt == "draw":
                st.draw(1)
                st.emit("Verduran Enchantress: draw a card")
            return None

        return branch_over(state, ["decline", "draw"], fn)
