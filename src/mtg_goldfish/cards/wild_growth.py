"""Wild Growth — {G} Aura — Enchant land.
Whenever enchanted land is tapped for mana, add an additional {G}.
Cast: attach to one of your lands (branch per distinct land)."""
from __future__ import annotations

from ._common import aura_on_land_cast_actions
from .base import Card
from .registry import register


@register
class WildGrowth(Card):
    card_name = "Wild Growth"

    def cast_actions(self, state):
        return aura_on_land_cast_actions(self, state)

    def attached_mana_amount_bonus(self, state, perm, host):
        return 1  # +{G}; colour flexibility of the extra mana is approximated
