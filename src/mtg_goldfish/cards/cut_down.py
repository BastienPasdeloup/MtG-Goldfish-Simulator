"""Cut Down — {B} Instant. Destroy target creature with total power and toughness
5 or less."""
from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class CutDown(Card):
    card_name = "Cut Down"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield if p.is_creature_now
                   and state.effective_power(p) + state.effective_toughness(p) <= 5]

        def effect(st, perm):
            if st.effective_power(perm) + st.effective_toughness(perm) <= 5:
                st.emit(f"Cut Down: destroy {perm.name}")
                st.leaves_battlefield(perm, "graveyard", reason="destroy")

        return targeted_instant_casts(self, state, targets, effect, tag="P+T≤5")
