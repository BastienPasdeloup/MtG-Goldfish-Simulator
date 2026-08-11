"""Animate Wall — {W} Enchantment — Aura. Enchant Wall.
Enchanted Wall can attack as though it didn't have defender.

Attaches to one of your Walls and strips its Defender keyword (via
removed_keywords) so it can attack; restored if the Aura leaves."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class AnimateWall(Card):
    card_name = "Animate Wall"

    def cast_actions(self, state):
        def is_wall(p):
            return p.is_creature_now and "wall" in p.type_line.lower()

        def on_attach(st, aura, host):
            host.removed_keywords.add("defender")  # can attack now

        return aura_enchant_actions(self, state, cost="{W}", pred=is_wall, on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.removed_keywords.discard("defender")
