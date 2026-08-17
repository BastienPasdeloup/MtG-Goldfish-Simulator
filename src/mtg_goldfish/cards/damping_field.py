"""Damping Field — {2}{W} Enchantment.
Players can't untap more than one artifact during their untap steps.

Caps your artifact untaps at one per turn (via the `untap_artifact_limit` hook) —
the same effect as Static Orb on artifacts."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DampingField(Card):
    card_name = "Damping Field"

    def untap_artifact_limit(self, state, perm):
        return 1
