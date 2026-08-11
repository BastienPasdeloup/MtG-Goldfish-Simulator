"""Vraan, Executioner Thane — {1}{B} Legendary Creature 2/2.
Whenever one or more other creatures you control die, each opponent loses 2 life
and you gain 2 life. This ability triggers only once each turn."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class VraanExecutionerThane(Card):
    card_name = "Vraan, Executioner Thane"

    def on_other_leave(self, state, perm, left, to, reason):
        if to != "graveyard" or not left.is_creature_now:
            return
        if perm.turn_flags.get("vraan_fired"):
            return
        perm.turn_flags["vraan_fired"] = 1
        state.damage_opponent(2)  # noncombat -> amplifiers apply
        state.gain_life(2)
        state.emit(f"Vraan: opponent loses 2 ({state.opponent_life}), "
                   f"you gain 2 ({state.life})")
