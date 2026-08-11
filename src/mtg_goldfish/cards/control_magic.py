"""Control Magic — {2}{U}{U} Enchantment — Aura. Enchant creature.
You control enchanted creature.

Gaining control only matters for an opponent's creature (none in a goldfish);
enchanting your own is a no-op — the Aura just attaches (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class ControlMagic(Card):
    card_name = "Control Magic"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{2}{U}{U}")
