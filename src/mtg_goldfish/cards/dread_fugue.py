"""Dread Fugue — {B} Sorcery, Cleave {2}{B}. Target player reveals their hand;
you choose a nonland card [with mana value 2 or less]; that player discards it.
Aim at yourself to bin a nonland (MV<=2 normally, any nonland if cleaved)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import discard_spell_actions, mv
from .base import Card
from .registry import register

_CLEAVE = ManaCost(generic=2, pips=(("B", 1),))


@register
class DreadFugue(Card):
    card_name = "Dread Fugue"

    def cast_actions(self, state):
        acts = discard_spell_actions(
            self, state, pred=lambda c: not c.is_land and mv(c) <= 2)
        # Cleave: pay {2}{B}, remove the bracketed restriction (any nonland).
        acts += discard_spell_actions(
            self, state, pred=lambda c: not c.is_land, cost=_CLEAVE)
        return acts
