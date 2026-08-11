"""Lord of Atlantis — {U}{U} Creature — Merfolk 2/2.
Other Merfolk get +1/+1 and have islandwalk.

A lord: a static +1/+1 anthem to every OTHER Merfolk (via static_pt_bonus,
excluding itself by uid). Islandwalk is evasion — inert with no opponent — so only
the P/T buff is materially modelled."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class LordOfAtlantis(Card):
    card_name = "Lord of Atlantis"

    def static_pt_bonus(self, state, source, perm):
        if (perm.uid != source.uid and perm.is_creature_now
                and "merfolk" in perm.type_line.lower()):
            return (1, 1)
        return (0, 0)
