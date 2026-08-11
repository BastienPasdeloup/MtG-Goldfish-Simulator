"""Cursed Land — {2}{B}{B} Enchantment — Aura. Enchant land.
At the beginning of the upkeep of enchanted land's controller, this Aura deals 1
damage to that player.

Enchant one of your lands (you are its controller); at your upkeep it deals 1 to
you — a self-damage downside."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class CursedLand(Card):
    card_name = "Cursed Land"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{2}{B}{B}",
                                    pred=lambda p: p.is_land)

    def on_phase(self, state, perm, phase):
        state.life -= 1
        state.emit("Cursed Land: deals 1 damage to you")
        return None
