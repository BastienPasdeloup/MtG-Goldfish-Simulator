"""Consecrate Land — {W} Enchantment — Aura. Enchant land.
Enchanted land has indestructible and can't be enchanted by other Auras.

Grants indestructible to your land (via extra_keywords) so it survives destroy
effects like Armageddon; removed if the Aura leaves."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class ConsecrateLand(Card):
    card_name = "Consecrate Land"

    def cast_actions(self, state):
        def on_attach(st, aura, host):
            host.extra_keywords.add("indestructible")

        return aura_enchant_actions(self, state, cost="{W}",
                                    pred=lambda p: p.is_land, on_attach=on_attach)

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.extra_keywords.discard("indestructible")
