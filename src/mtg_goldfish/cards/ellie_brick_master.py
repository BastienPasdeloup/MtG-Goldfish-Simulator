"""Ellie, Brick Master — {1}{R} Legendary Creature 2/1. Partner—Survivors.
Distract the Horde — Whenever a player attacks one of your opponents, that
attacking player creates a tapped 1/1 black Fungus Zombie token named Cordyceps
Infected that's attacking that opponent. In a goldfish you are the attacking
player, so this makes you one tapped, attacking token each time you attack."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class EllieBrickMaster(Card):
    card_name = "Ellie, Brick Master"

    def on_you_attack(self, state, perm):
        tok = state.make_token("Cordyceps Infected", 1, 1, "Creature — Fungus Zombie")
        tok.tapped = True
        tok.summoning_sick = False
        state.attackers.append(tok.uid)
        state.emit("Distract the Horde: create a tapped, attacking 1/1 Fungus Zombie")
