"""Goblin King — {1}{R}{R} Creature — Goblin 2/2.
Other Goblins get +1/+1 and have mountainwalk.

A lord: a static anthem (+1/+1) to every OTHER Goblin on the battlefield (via
static_pt_bonus, excluding itself by uid). Mountainwalk is evasion — inert with no
opponent to be walked past — so only the P/T buff is materially modelled."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GoblinKing(Card):
    card_name = "Goblin King"

    def static_pt_bonus(self, state, source, perm):
        if (perm.uid != source.uid and perm.is_creature_now
                and "goblin" in perm.type_line.lower()):
            return (1, 1)
        return (0, 0)
