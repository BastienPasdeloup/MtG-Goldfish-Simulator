"""Feedback — {2}{U} Enchantment — Aura. Enchant enchantment.
At the beginning of the upkeep of enchanted enchantment's controller, this Aura
deals 1 damage to that player.

Enchant one of your enchantments; at your upkeep it deals 1 to you (via
damage_self, so prevention applies)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Feedback(Card):
    card_name = "Feedback"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{2}{U}",
                                    pred=lambda p: "enchantment" in p.type_line.lower())

    def on_phase(self, state, perm, phase):
        state.emit("Feedback: 1 damage to you")
        state.damage_self(1, colors=("U",))
        return None
