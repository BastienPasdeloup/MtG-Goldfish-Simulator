"""Power Artifact — {U}{U} Enchantment — Aura. Enchant artifact.
Enchanted artifact's activated abilities cost {2} less to activate (never below one
mana).

Grants a per-host {2} discount (`enchanted_ability_discount`) applied by
`artifact_ability_cost(state, cost, perm=host)` — so an artifact whose abilities
route their cost through that helper is cheaper to activate. Classic combo: on
Basalt Monolith the {3} untap becomes {1} (with its {T}: add {C}{C}{C}, that is net
+2 mana per cycle — an infinite-mana engine the search can exploit)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class PowerArtifact(Card):
    card_name = "Power Artifact"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost=self.cast_cost(state),
                                    pred=lambda p: p.is_artifact)

    def enchanted_ability_discount(self, state, aura, host):
        return 2
