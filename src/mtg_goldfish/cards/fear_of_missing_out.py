"""Fear of Missing Out — {1}{R} Enchantment Creature 2/3.
When it enters, discard a card, then draw a card.
Delirium — Whenever it attacks for the first time each turn, if there are four or
more card types among cards in your graveyard, untap target creature. (The
additional combat phase is not modelled — the engine has a fixed turn.)"""
from __future__ import annotations

from ._common import branch_over, graveyard_card_types
from .base import Card
from .registry import register


@register
class FearOfMissingOut(Card):
    card_name = "Fear of Missing Out"

    def on_etb(self, state, permanent):
        others = {c.name for c in state.hand}
        if not others:
            state.draw(1)
            state.emit("Fear of Missing Out: no card to discard, draw 1")
            return None

        def fn(st, name):
            c = next((x for x in st.hand if x.name == name), None)
            if c is not None:
                st.discard(c)
            st.draw(1)
            return None

        return branch_over(state, sorted(others), fn)

    def on_attack(self, state, perm):
        if perm.turn_flags.get("fomo_attacked"):
            return
        perm.turn_flags["fomo_attacked"] = 1
        if len(graveyard_card_types(state)) < 4:
            return
        tgt = next((p for p in state.battlefield
                    if p.is_creature_now and p.tapped and p.uid != perm.uid), None)
        if tgt is not None:
            tgt.tapped = False
            state.emit(f"Fear of Missing Out: delirium — untap {tgt.name}")
        state.emit("Fear of Missing Out: delirium extra combat phase not modelled")
