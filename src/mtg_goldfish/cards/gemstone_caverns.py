"""Gemstone Caverns — Legendary Land.
If this card is in your opening hand and you're not the starting player, you may
begin the game with it on the battlefield with a luck counter, exiling a card
from your hand.
{T}: Add {C}. If it has a luck counter on it, instead add one mana of any color.

The opening-hand start is modelled in the simulator (see `_apply_start_of_game`):
when you're on the DRAW and it's in your opening hand, you begin the game with it
on the battlefield carrying a luck counter (exiling a card from your hand). On
the play it's a normal colourless land in hand. This mana ability produces one
mana of any colour in your identity when a luck counter is present (either the
on-the-draw start, or a Fixed-config setup), else {C}."""
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
