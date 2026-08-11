"""Web — {G} Enchantment — Aura. Enchant creature.
Enchanted creature gets +0/+2 and has reach.

Static +0/+2 via equip_mod plus the reach keyword (inert with no attackers to
block, but genuinely granted)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Web(Card):
    card_name = "Web"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.extra_keywords.add("reach")

        return aura_enchant_actions(self, state, cost="{G}", on_attach=on_attach)

    def equip_mod(self, state, perm):
        return (0, 2)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.extra_keywords.discard("reach")
