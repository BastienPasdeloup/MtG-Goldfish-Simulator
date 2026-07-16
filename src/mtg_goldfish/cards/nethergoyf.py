"""Nethergoyf — {B} Creature */1+*, escape.
Power = number of card types among cards in your graveyard; toughness = that + 1.
Escape—{2}{B}, Exile any number of other cards from your graveyard with four or
more card types among them. (Exiles a minimal type-covering set, not branched.)"""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import _CARD_TYPES, graveyard_card_types
from .base import Card, CardAction
from .registry import register


@register
class Nethergoyf(Card):
    card_name = "Nethergoyf"

    def dynamic_power(self, state, perm):
        return len(graveyard_card_types(state))

    def dynamic_toughness(self, state, perm):
        return len(graveyard_card_types(state)) + 1

    def graveyard_actions(self, state):
        from ..engine.actions import (begin_cast, can_afford,
                                      resolve_to_battlefield)

        cost = ManaCost(generic=2, pips=(("B", 1),))
        pool = [c for c in state.graveyard if c.name != self.card_name]
        available = set()
        for c in pool:
            available |= {t for t in _CARD_TYPES if t in c.type_line.lower()}
        if len(available) < 4 or not can_afford(state, cost):
            return []

        def fn(st):
            me = next((c for c in st.graveyard if c.name == self.card_name), None)
            if me is None:
                return None
            picks, covered = [], set()
            for c in [x for x in st.graveyard if x.name != self.card_name]:
                tset = {t for t in _CARD_TYPES if t in c.type_line.lower()}
                if tset - covered:
                    picks.append(c)
                    covered |= tset
                if len(covered) >= 4:
                    break
            if len(covered) < 4:
                return None
            if not begin_cast(st, me, cost, zone=st.graveyard, tag="escape"):
                return None
            for c in picks:
                if c in st.graveyard:
                    st.graveyard.remove(c)
                    st.exile.append(c)
            st.left_graveyard_this_turn = True
            st.emit(f"Nethergoyf escape: exile {len(picks)} cards "
                    f"({len(covered)} types)")
            return resolve_to_battlefield(st, me) or None

        return [CardAction("cast Nethergoyf (escape)", fn)]
