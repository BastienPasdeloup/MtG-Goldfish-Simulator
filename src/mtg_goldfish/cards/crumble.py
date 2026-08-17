"""Crumble — {G} Instant.
Destroy target artifact. It can't be regenerated. That artifact's controller
gains life equal to its mana value.

One branch per distinct artifact you control; YOU are its controller, so you gain
life equal to its mana value."""
from __future__ import annotations

from ._common import mv, targeted_instant_casts
from .base import Card
from .registry import register


@register
class Crumble(Card):
    card_name = "Crumble"

    def cast_actions(self, state):
        seen, uids = set(), []
        for p in state.battlefield:
            if p.is_artifact and p.name not in seen:
                seen.add(p.name)
                uids.append(p.uid)

        def effect(st, perm):
            amt = mv(perm.card)
            perm.counters.pop("regen_shield", None)  # can't be regenerated
            st.emit(f"Crumble: destroy {perm.name}")
            st.leaves_battlefield(perm, "graveyard", reason="destroy")
            if amt > 0:
                st.gain_life(amt)
                st.emit(f"Crumble: controller gains {amt} life ({st.life})")
            st.check_deaths()

        return targeted_instant_casts(self, state, uids, effect)
