"""Ali from Cairo — {2}{R}{R} Creature — Human 0/1.
Damage that would reduce your life total to less than 1 reduces it to 1 instead.

A life-floor static: while Ali is in play, damage can never take you below 1 life
(via caps_life_at_one, checked in GameState.damage_self)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AliFromCairo(Card):
    card_name = "Ali from Cairo"

    def caps_life_at_one(self, state, perm):
        return True
