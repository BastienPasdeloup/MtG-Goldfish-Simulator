"""Drain Power — {U}{U} Sorcery.
Target player activates a mana ability of each land they control. Then that player
loses all unspent mana and you add the mana lost this way.

Aimed at an opponent (none in a goldfish); targeting yourself, you tap each of
your lands for mana into your own pool — net-neutral but the ability is modelled
(it does force-tap all your lands)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DrainPower(Card):
    card_name = "Drain Power"

    def on_resolve(self, state):
        from ..engine.actions import available_mana_sources

        added = 0
        for perm, ability in available_mana_sources(state):
            if perm.is_land and not perm.tapped:
                perm.tapped = True
                color = "C" if "C" in ability.choices else ability.choices[0]
                state.mana_pool.add(color, ability.amount)
                added += ability.amount
        state.emit(f"Drain Power: tap your lands for {added} mana into your pool")
