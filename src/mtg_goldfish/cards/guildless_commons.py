"""Guildless Commons — Land.
Enters tapped. ETB: return a land you control to its owner's hand (branch;
the Commons itself is a legal choice). {T}: Add {C}{C}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import branch_over
from .base import Card
from .registry import register


@register
class GuildlessCommons(Card):
    card_name = "Guildless Commons"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=2, choices=("C",))]

    def on_etb(self, state, permanent):
        lands = {}
        for p in state.battlefield:
            if "land" in p.type_line.lower() and p.name not in lands:
                lands[p.name] = p.uid
        if not lands:
            return None

        def fn(st, uid):
            p = st.find_permanent(uid)
            if p is not None:
                st.emit(f"Guildless Commons: return {p.name} to hand")
                st.leaves_battlefield(p, "hand")

        return branch_over(state, list(lands.values()), fn)
