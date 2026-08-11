"""Desert — Land — Desert.
{T}: Add {C}.
{T}: This land deals 1 damage to target attacking creature. Only during the end of
combat step.

Taps for {C}. The 1-damage ability can only hit an ATTACKING creature — in a
solitaire goldfish that means your own attacker, never worth it — so only the mana
ability is offered."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Desert(Card):
    card_name = "Desert"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
