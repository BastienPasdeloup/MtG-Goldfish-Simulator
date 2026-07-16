"""Demonic Consultation — {B} Instant. Choose a card name; exile the top six
cards; then reveal from the top until you reveal a card with the chosen name, put
it into your hand, and exile all other cards revealed this way.
Branches over naming a card that lies deeper than the top six (so it is actually
found) — naming a shallower card would just exile the library."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class DemonicConsultation(Card):
    card_name = "Demonic Consultation"

    def on_resolve(self, state):
        if len(state.library) <= 6:
            state.exile.extend(state.library)
            state.library.clear()
            state.emit("Demonic Consultation: exiled the whole library")
            return None
        deep = sorted({c.name for c in state.library[6:]})

        def fn(st, name):
            for _ in range(6):
                st.exile.append(st.library.pop(0))
            while st.library:
                c = st.library.pop(0)
                if c.name == name:
                    st.hand.append(c)
                    st.emit(f"Demonic Consultation: named {name} — to hand")
                    return None
                st.exile.append(c)
            st.emit(f"Demonic Consultation: {name} not found — library exiled")
            return None

        return branch_over(state, deep, fn)
