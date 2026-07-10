"""Vesuva — Land.
May enter tapped as a copy of any land on the battlefield: one branch per
distinct land you control (the copy keeps that land's abilities via its own
implementation), plus an uncopied branch (a land with no abilities)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class Vesuva(Card):
    card_name = "Vesuva"

    def etb_tapped(self, state):
        return True

    def on_etb(self, state, permanent):
        from .registry import build_card

        names = {}
        for p in state.battlefield:
            if p.uid != permanent.uid and "land" in p.type_line.lower() and p.name not in names:
                names[p.name] = p.card

        if not names:
            return None

        def fn(st, name):
            p = st.find_permanent(permanent.uid)
            if p is None:
                return None
            src = names[name]
            p.card = src.model_copy()
            p.impl = build_card(p.card)
            p.tapped = True
            st.emit(f"Vesuva enters as a copy of {name} (tapped)")

        branches = branch_over(state, sorted(names), fn)
        plain = state.clone()
        plain.emit("Vesuva enters uncopied (tapped, no abilities)")
        return branches + [plain]
