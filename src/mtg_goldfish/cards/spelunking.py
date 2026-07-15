"""Spelunking — {2}{G} Enchantment.
ETB: draw a card, then you may put a land card from your hand onto the
battlefield (branch per distinct land, plus declining; a Cave gains 4 life).
Static: lands you control enter untapped (untap any land that enters tapped)."""
from __future__ import annotations

from ._common import branch_over, enter_battlefield
from .base import Card
from .registry import register


@register
class Spelunking(Card):
    card_name = "Spelunking"

    def on_other_etb_immediate(self, state, perm, entering):
        # Replacement effect: untap silently so the land is shown untapped in the
        # very frame it enters, rather than flashing tapped first.
        if entering.is_land and entering.tapped:
            entering.tapped = False

    def on_etb(self, state, permanent):
        state.draw(1)
        state.emit("Spelunking: draw a card")
        names = sorted({c.name for c in state.hand if c.is_land})
        if not names:
            return None

        def fn(st, name):
            if name is None:
                return
            card = next((c for c in st.hand if c.name == name), None)
            if card is None:
                return
            st.hand.remove(card)
            newp = enter_battlefield(
                st,
                card,
                announce=f"Spelunking: put {name} onto the battlefield",
            )
            if "cave" in newp.type_line.lower():
                st.life += 4
                st.emit("Spelunking: Cave entered — gain 4 life")

        return branch_over(state, names + [None], fn)
