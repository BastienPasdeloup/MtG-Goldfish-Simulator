"""Meekstone — {1} Artifact.
Creatures with power 3 or greater don't untap during their controllers' untap
steps.

Symmetric static effect — in a solitaire goldfish it holds YOUR power-3+ creatures
tapped once they tap (e.g. after attacking), via the untap-step `prevents_untap`
broadcast."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Meekstone(Card):
    card_name = "Meekstone"

    def prevents_untap(self, state, source, perm):
        return perm.is_creature_now and state.effective_power(perm) >= 3
