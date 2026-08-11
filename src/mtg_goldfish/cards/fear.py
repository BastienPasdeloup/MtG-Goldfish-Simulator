"""Fear — {B}{B} Enchantment — Aura. Enchant creature.
Enchanted creature has fear (can't be blocked except by artifact and/or black
creatures).

Grants the fear keyword to the host (via extra_keywords). Evasion has no effect
with no blockers, but the keyword is genuinely granted (and the Aura is cast and
on the board)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Fear(Card):
    card_name = "Fear"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.extra_keywords.add("fear")

        return aura_enchant_actions(self, state, cost="{B}{B}", on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.extra_keywords.discard("fear")
