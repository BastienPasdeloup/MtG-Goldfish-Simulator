"""Creature Bond — {1}{U} Enchantment — Aura. Enchant creature.
When enchanted creature dies, this Aura deals damage equal to that creature's
toughness to the creature's controller.

Enchant one of your creatures; when it DIES (to a graveyard) it deals its
toughness to you (via the on_enchanted_leaves aura hook + damage_self)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class CreatureBond(Card):
    card_name = "Creature Bond"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{U}")

    def on_enchanted_leaves(self, state, perm, host, to, reason):
        if to == "graveyard":  # the enchanted creature died
            dmg = max(0, state.effective_toughness(host))
            state.emit(f"Creature Bond: {host.name} died — {dmg} damage to you")
            state.damage_self(dmg, colors=("U",))
