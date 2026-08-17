"""Haunting Wind — {3}{B} Enchantment.
Whenever an artifact becomes tapped or a player activates an artifact's ability
without {T} in its activation cost, this enchantment deals 1 damage to that
artifact's controller.

Symmetric self-damage: each of YOUR artifacts tapped for mana pings you 1 (via the
`on_artifact_tapped_for_mana` broadcast). The "non-{T} artifact ability" half is
rare in a goldfish and left out (only the tap half is broadcast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HauntingWind(Card):
    card_name = "Haunting Wind"

    def on_artifact_tapped_for_mana(self, state, perm, artifact):
        state.damage_self(1, by_artifact=True)
        state.emit(f"Haunting Wind: 1 damage to you ({artifact.name} tapped) — life {state.life}")
