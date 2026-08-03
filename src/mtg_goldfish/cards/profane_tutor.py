"""Profane Tutor — Suspend 2—{1}{B}. Search your library for a card, put it into
your hand, then shuffle.
Approximation: it has no normal mana cost (only Suspend), which the engine does
not model (no time counters). It is treated as a sorcery-speed tutor costing
{1}{B} that resolves immediately — this UNDERSTATES its real cost by the two-turn
suspend delay."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import tutor_to_hand_branches
from .base import Card, CardAction
from .registry import register

_SUSPEND = ManaCost(generic=1, pips=(("B", 1),))


@register
class ProfaneTutor(Card):
    card_name = "Profane Tutor"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        if not can_afford(state, _SUSPEND):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, _SUSPEND):
                return None
            resolve_to_graveyard(st, card)
            st.emit("Profane Tutor: (suspend approximated as immediate) search a card")
            return tutor_to_hand_branches(st, lambda c: True)

        return [CardAction("cast Profane Tutor (suspend {1}{B})", fn)]
