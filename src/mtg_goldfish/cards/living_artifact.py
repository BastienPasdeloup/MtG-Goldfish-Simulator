"""Living Artifact — {G} Enchantment — Aura. Enchant artifact.
Whenever you're dealt damage, put that many vitality counters on this Aura.
At the beginning of your upkeep, you may remove a vitality counter from this Aura.
If you do, you gain 1 life.

Enchant one of your artifacts. Each point of damage YOU take (via on_owner_damaged)
banks a vitality counter; each of your upkeeps offers a branch: remove a vitality
counter and gain 1 life, or decline."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions, branch_over
from .base import Card
from .registry import register


@register
class LivingArtifact(Card):
    card_name = "Living Artifact"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{G}",
                                    pred=lambda p: p.is_artifact)

    def on_owner_damaged(self, state, perm, amount):
        p = state.find_permanent(perm.uid)
        if p is not None and amount > 0:
            p.counters["vitality"] = p.counters.get("vitality", 0) + amount
            state.emit(f"Living Artifact: bank {amount} vitality counter(s)")
        return None

    def on_phase(self, state, perm, phase):
        p = state.find_permanent(perm.uid)
        if p is None or p.counters.get("vitality", 0) <= 0:
            return None

        def fn(st, opt):
            live = st.find_permanent(perm.uid)
            if opt == "gain" and live is not None and live.counters.get("vitality", 0) > 0:
                live.counters["vitality"] -= 1
                st.gain_life(1)
                st.emit("Living Artifact: remove a vitality counter, gain 1 life")
            return None

        return branch_over(state, ["decline", "gain"], fn)
