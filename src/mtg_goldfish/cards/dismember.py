"""Dismember — {1}{B/P}{B/P} Instant. Target creature gets -5/-5 until end of
turn. Each {B/P} is paid with {B} or 2 life — payment variants are branches.
Only your own creatures are legal targets in solitaire."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import targeted_instant_casts
from .base import Card
from .registry import register

_PAYMENTS = [
    (ManaCost(generic=1, pips=(("B", 2),)), 0, "{1}{B}{B}"),
    (ManaCost(generic=1, pips=(("B", 1),)), 2, "{1}{B} + 2 life"),
    (ManaCost(generic=1), 4, "{1} + 4 life"),
]


@register
class Dismember(Card):
    card_name = "Dismember"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield if p.is_creature_now]

        def effect(st, perm):
            perm.temp_power -= 5
            perm.temp_toughness -= 5
            st.emit(f"Dismember: {perm.name} gets -5/-5")

        actions = []
        for cost, life, tag in _PAYMENTS:
            actions.extend(
                targeted_instant_casts(self, state, targets, effect,
                                       cost=cost, extra_life=life, tag=tag)
            )
        return actions
