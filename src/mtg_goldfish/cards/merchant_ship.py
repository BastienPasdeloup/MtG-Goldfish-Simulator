"""Merchant Ship — {U} Creature — Human 0/2.
This creature can't attack unless defending player controls an Island.
Whenever this creature attacks and isn't blocked, you gain 2 life.
When you control no Islands, sacrifice this creature.

The attack restriction / lifegain depend on the opponent's Islands (never any → it
can't attack). It is sacrificed at your upkeep if you control no Island."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class MerchantShip(Card):
    card_name = "Merchant Ship"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        if not any(p.is_land and "island" in p.type_line.lower() for p in state.battlefield):
            p = state.find_permanent(perm.uid)
            if p is not None:
                state.emit("Merchant Ship: no Island — sacrifice")
                state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
