"""Lance — {W} Enchantment — Aura. Enchant creature.
Enchanted creature has first strike.

Grants the first-strike keyword to the host (via extra_keywords). With no blockers
first strike has no combat effect, but the keyword is genuinely granted."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Lance(Card):
    card_name = "Lance"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.extra_keywords.add("first strike")

        return aura_enchant_actions(self, state, cost="{W}", on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.extra_keywords.discard("first strike")
