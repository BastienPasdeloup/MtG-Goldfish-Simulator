"""Ghazbán Ogre — {G} Creature — Ogre 2/2.
At the beginning of your upkeep, if a player has more life than each other player,
the player with the most life gains control of this creature.

In a solitaire goldfish: if the (phantom) opponent has strictly more life than you,
it gains control of the Ogre — modelled as the Ogre leaving your battlefield. While
you are at ≥ the opponent's life you keep it (a cheap 2/2 with an upside/drawback)."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class GhazbanOgre(Card):
    card_name = "Ghazbán Ogre"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        if state.opponent_life > state.life:
            p = state.find_permanent(perm.uid)
            if p is not None:
                state.emit("Ghazbán Ogre: opponent has more life — you lose control")
                state.leaves_battlefield(p, "exile", reason="control")
        return None
