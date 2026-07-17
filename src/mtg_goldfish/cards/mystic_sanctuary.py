"""Mystic Sanctuary — Land — Island. {T}: Add {U}. Enters tapped unless you
control three or more other Islands. When it enters untapped, you may put a
target instant or sorcery card from your graveyard on top of your library."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import branch_over, perm_has_subtype
from .base import Card
from .registry import register


@register
class MysticSanctuary(Card):
    card_name = "Mystic Sanctuary"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def etb_tapped(self, state):
        islands = sum(1 for p in state.battlefield
                      if p.is_land and perm_has_subtype(p, ("Island",)))
        return islands < 3

    def on_etb(self, state, permanent):
        if permanent.tapped:
            return None
        targets = sorted({c.name for c in state.graveyard
                          if c.is_instant or c.is_sorcery})
        if not targets:
            return None
        options = ["(none)"] + targets

        def fn(st, name):
            if name != "(none)":
                c = next((x for x in st.graveyard if x.name == name), None)
                if c is not None:
                    st.graveyard.remove(c)
                    st.library.insert(0, c)
                    st.emit(f"Mystic Sanctuary: put {name} on top of library")
            return None

        return branch_over(state, options, fn)
