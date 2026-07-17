"""Long Goodbye — {1}{B} Instant. Can't be countered. Destroy target creature or
planeswalker with mana value 3 or less."""
from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class LongGoodbye(Card):
    card_name = "Long Goodbye"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield if p.card.cmc <= 3
                   and (p.is_creature_now or "planeswalker" in p.type_line.lower())]

        def effect(st, perm):
            st.emit(f"Long Goodbye: destroy {perm.name}")
            st.leaves_battlefield(perm, "graveyard", reason="destroy")

        return targeted_instant_casts(self, state, targets, effect, tag="mv≤3")
