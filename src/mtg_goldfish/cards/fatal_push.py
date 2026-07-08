"""Fatal Push — {B} Instant. Destroy target creature if it has mana value 2 or
less (4 or less with revolt: a permanent left the battlefield this turn).
Only your own creatures are legal targets in a solitaire game."""
from __future__ import annotations

from ._common import targeted_instant_casts
from .base import Card
from .registry import register


@register
class FatalPush(Card):
    card_name = "Fatal Push"

    def cast_actions(self, state):
        limit = 4 if state.permanent_left_battlefield_this_turn else 2
        targets = [p.uid for p in state.battlefield if p.is_creature_now]

        def effect(st, perm):
            lim = 4 if st.permanent_left_battlefield_this_turn else 2
            if perm.card.cmc <= lim:
                st.emit(f"Fatal Push: destroy {perm.name}")
                st.leaves_battlefield(perm, "graveyard")
            else:
                st.emit(f"Fatal Push: {perm.name} survives (mv > {lim})")

        tag = f"revolt, mv≤{limit}" if limit == 4 else f"mv≤{limit}"
        return targeted_instant_casts(self, state, targets, effect, tag=tag)
