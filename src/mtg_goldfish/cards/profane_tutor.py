"""Profane Tutor — Suspend 2—{1}{B}. Search your library for a card, put it into
your hand, then shuffle.

Real suspend is modelled (see GameState.suspended + the UPKEEP resolution in the
simulator): casting it pays {1}{B} and exiles it with 2 time counters; one is
removed at the beginning of each of your upkeeps, and when the last is removed the
tutor resolves for free (~two turns later). It has NO normal mana cost — Suspend
is the only way to cast it."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import tutor_to_hand_branches
from .base import Card, CardAction
from .registry import register

_SUSPEND = ManaCost(generic=1, pips=(("B", 1),))
_SUSPEND_N = 2


@register
class ProfaneTutor(Card):
    card_name = "Profane Tutor"

    def cast_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        if not can_afford(state, _SUSPEND):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, _SUSPEND):
                return None
            st.hand.remove(card)
            st.exile.append(card)
            st.suspended.append({"card": card, "counters": _SUSPEND_N, "name": self.card_name})
            st.emit(f"suspend {self.card_name} — exiled with {_SUSPEND_N} time counters")
            return None

        return [CardAction(f"suspend Profane Tutor (suspend {_SUSPEND_N}—{{1}}{{B}})", fn)]

    def on_suspend_resolve(self, state):
        state.emit("Profane Tutor: last time counter removed — search a card")
        return tutor_to_hand_branches(state, lambda c: True)
