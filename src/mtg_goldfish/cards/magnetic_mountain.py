"""Magnetic Mountain — {1}{R}{R} Enchantment.
Blue creatures don't untap during their controllers' untap steps.
At the beginning of each player's upkeep, that player may choose any number of
tapped blue creatures they control and pay {4} for each to untap them.

The main effect is modelled: your blue creatures don't untap (via prevents_untap).
The pay-{4}-each option to untap them is not modelled (a symmetric downside on
blue creatures)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MagneticMountain(Card):
    card_name = "Magnetic Mountain"

    def prevents_untap(self, state, source, perm):
        return perm.is_creature_now and "U" in perm.colors
