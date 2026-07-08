"""Cloud, Midgar Mercenary — {W}{W} 2/1. When Cloud enters, search your library
for an Equipment card, reveal it, put it into your hand, then shuffle (branch;
declining the find is also a branch). The equipped-double-trigger clause has no
modelled triggers to double."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class CloudMidgarMercenary(Card):
    card_name = "Cloud, Midgar Mercenary"

    def on_etb(self, state, permanent):
        candidates = state.search_library(lambda c: "Equipment" in c.type_line)
        options: list[str | None] = [c.name for c in candidates] + [None]
        if not candidates:
            state.shuffle_library()
            state.emit("Cloud: no Equipment found — shuffle")
            return None

        def apply(st, name: str | None):
            if name is not None:
                card = next(c for c in st.library if c.name == name)
                st.take_from_library(card)
                st.hand.append(card)
            st.shuffle_library()
            st.emit(f"Cloud: {name or 'fail to find'} — shuffle")

        return branch_over(state, options, apply)
