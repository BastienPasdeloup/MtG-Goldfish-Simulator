"""Evil Presence — {B} Enchantment — Aura. Enchant land.
Enchanted land is a Swamp.

Overrides the enchanted land's mana so it taps for {B} (via mana_override); the
override is removed if the Aura leaves."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class EvilPresence(Card):
    card_name = "Evil Presence"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.mana_override = "B"  # is a Swamp

        return aura_enchant_actions(self, state, cost="{B}",
                                    pred=lambda p: p.is_land, on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.mana_override = None
