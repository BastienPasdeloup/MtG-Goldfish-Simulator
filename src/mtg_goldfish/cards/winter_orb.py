"""Winter Orb — {2} Artifact.
As long as Winter Orb is untapped, players can't untap more than one land during
their untap steps.

Symmetric stax: in a solitaire goldfish "players" is just you, so it restricts
YOUR own untap step to one land (a real downside the search will weigh). Modelled
via the untap-step limit hook."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WinterOrb(Card):
    card_name = "Winter Orb"

    def untap_land_limit(self, state, perm):
        return 1 if not perm.tapped else None
