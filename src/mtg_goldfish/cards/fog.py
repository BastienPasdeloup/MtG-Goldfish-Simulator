"""Fog — {G} Instant.
Prevent all combat damage that would be dealt this turn.

Sets the turn-scoped `prevent_all_combat_damage` flag, checked in
deal_combat_damage. In a solitaire goldfish there is no opponent attack, so this
only ever prevents YOUR OWN attackers' damage — the search won't cast it into its
own combat, but the effect is faithfully implemented."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Fog(Card):
    card_name = "Fog"

    def on_resolve(self, state):
        state.prevent_all_combat_damage = True
        state.emit("Fog: all combat damage prevented this turn")
