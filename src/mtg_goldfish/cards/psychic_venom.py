"""Psychic Venom — {1}{U} Enchantment — Aura. Enchant land.
Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's
controller.

Enchant one of your lands; each time THAT land is tapped for mana it deals you 2
(via damage_self, blue source) — pure self-harm in a solitaire goldfish, but the
Aura is a real effect and is offered. Fired by the land-tap broadcast in
pay_cost."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class PsychicVenom(Card):
    card_name = "Psychic Venom"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{U}",
                                    pred=lambda p: p.is_land)

    def on_land_tapped_for_mana(self, state, perm, land, color):
        if perm.attached_to == land.uid:
            state.damage_self(2, colors=("U",))
            state.emit(f"Psychic Venom: 2 damage to you ({land.name} tapped)")
        return None
