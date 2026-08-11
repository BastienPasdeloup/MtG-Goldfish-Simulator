"""Gauntlet of Might — {4} Artifact.
Red creatures get +1/+1.
Whenever a Mountain is tapped for mana, its controller adds an additional {R}.

The anthem (red creatures +1/+1) is modelled via static_pt_bonus. The
Mountain-mana boost is modelled in available_mana_sources (each Mountain adds an
extra {R} while a Gauntlet is in play — see `mountain_mana_bonus`)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GauntletOfMight(Card):
    card_name = "Gauntlet of Might"

    def static_pt_bonus(self, state, source, perm):
        if perm.is_creature_now and "R" in perm.colors:
            return (1, 1)
        return (0, 0)

    # Signals to available_mana_sources that Mountains produce an extra {R}.
    def mountain_mana_bonus(self, state, perm):
        return 1
