"""Gemstone Caverns — Legendary Land.
If this card is in your opening hand and you're not the starting player, you may
begin the game with it on the battlefield with a luck counter, exiling a card
from your hand.
{T}: Add {C}. If it has a luck counter on it, instead add one mana of any color.

The opening-hand start (a start-of-game replacement that only applies when you're
on the draw) isn't modelled — played normally it enters as a colourless land.
If a luck counter is present (e.g. set up in the Fixed-config editor), it taps
for one mana of any colour in your identity instead."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class GemstoneCaverns(Card):
    card_name = "Gemstone Caverns"

    def mana_abilities_perm(self, state, perm):
        if perm.counters.get("luck", 0) >= 1:
            return [ManaAbility(amount=1, choices=any_identity_color(state))]
        return [ManaAbility(amount=1, choices=("C",))]
