"""Smoke — {R}{R} Enchantment.
Players can't untap more than one creature during their untap steps.

Symmetric — you may untap at most one creature each untap step (via the
untap_creature_limit hook), so a wide board that taps out stays mostly tapped."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Smoke(Card):
    card_name = "Smoke"

    def untap_creature_limit(self, state, perm):
        return 1
