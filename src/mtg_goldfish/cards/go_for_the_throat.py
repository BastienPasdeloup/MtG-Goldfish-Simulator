"""Go for the Throat — {1}{B} Instant. Destroy target nonartifact creature."""
from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class GoForTheThroat(Card):
    card_name = "Go for the Throat"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield
                   if p.is_creature_now and "artifact" not in p.type_line.lower()]

        def effect(st, perm):
            st.emit(f"Go for the Throat: destroy {perm.name}")
            st.leaves_battlefield(perm, "graveyard", reason="destroy")

        return targeted_instant_casts(self, state, targets, effect)
