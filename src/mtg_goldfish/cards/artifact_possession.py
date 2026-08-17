"""Artifact Possession — {2}{B} Enchantment — Aura. Enchant artifact.
Whenever enchanted artifact becomes tapped or a player activates an ability of it
without {T}, this Aura deals 2 damage to that artifact's controller.

Aimed at an OPPONENT's artifact; in a goldfish the only legal host is your own
artifact, so it would only ever hurt you — the search never casts it. Still
implemented faithfully: enchant one of your artifacts (one branch each), and when
that artifact taps for mana it deals 2 to you (via the tap broadcast)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class ArtifactPossession(Card):
    card_name = "Artifact Possession"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost=self.cast_cost(state),
                                    pred=lambda p: p.is_artifact)

    def on_artifact_tapped_for_mana(self, state, perm, artifact):
        if perm.attached_to == artifact.uid:
            state.damage_self(2, by_artifact=True)
            state.emit(f"Artifact Possession: 2 damage to you ({artifact.name} tapped) — life {state.life}")
