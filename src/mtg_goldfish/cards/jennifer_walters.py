"""Jennifer Walters // The Sensational She-Hulk — {1}{W} Legendary 2/3.
"Your opponents can't cast spells during your turn" — opponent-facing, no
effect in solitaire. {3}{G}{W}{W}: transform into the 6/6 (sorcery). The
She-Hulk damage-redirect trigger needs incoming damage — not modelled."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card
from .registry import register


@register
class JenniferWalters(Card):
    card_name = "Jennifer Walters // The Sensational She-Hulk"

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=3, pips=(("G", 1), ("W", 2))),
            "The Sensational She-Hulk",
        )
