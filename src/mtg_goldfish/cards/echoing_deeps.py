"""Echoing Deeps — Land — Cave.
May enter (tapped) as a copy of a land card in a graveyard: one branch per
distinct land card in your graveyard (the copy keeps its printed abilities via
its own implementation), plus the plain '{T}: Add {C}' Cave."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import branch_over
from .base import Card
from .registry import register


@register
class EchoingDeeps(Card):
    card_name = "Echoing Deeps"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def on_etb(self, state, permanent):
        from .registry import build_card

        names = sorted({c.name for c in state.graveyard if c.is_land})
        if not names:
            return None

        def fn(st, name):
            p = st.find_permanent(permanent.uid)
            src = next((c for c in st.graveyard if c.name == name), None)
            if p is None or src is None:
                return None  # plain Cave
            p.card = src.model_copy()
            p.impl = build_card(p.card)
            p.tapped = True
            st.emit(f"Echoing Deeps enters as a copy of {name} (tapped)")

        # The "no copy" branch is the unmodified state (also returned).
        branches = branch_over(state, names, fn)
        plain = state.clone()
        plain.emit("Echoing Deeps enters as itself (tapped)")
        return branches + [plain]
