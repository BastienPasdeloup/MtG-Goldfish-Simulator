"""Utopia Sprawl — {G} Aura — Enchant Forest.
As it enters, choose a color. Whenever enchanted Forest is tapped for mana,
add an additional mana of the chosen color. Cast: attach to one of your
Forests (branch). The extra mana is modelled as +1 (any identity color folds
into generic anyway for this deck)."""
from __future__ import annotations

from ._common import aura_on_land_cast_actions
from .base import Card
from .registry import register


@register
class UtopiaSprawl(Card):
    card_name = "Utopia Sprawl"

    def cast_actions(self, state):
        return aura_on_land_cast_actions(self, state, forests_only=True)

    def attached_mana_amount_bonus(self, state, perm, host):
        return 1
