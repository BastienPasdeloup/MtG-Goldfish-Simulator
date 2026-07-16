"""Snuff Out — {3}{B} Instant. If you control a Swamp, you may pay 4 life instead
of the mana cost. Destroy target nonblack creature; it can't be regenerated.
Only your own creatures are legal targets in a goldfish."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import perm_has_subtype, targeted_instant_casts
from .base import Card
from .registry import register


@register
class SnuffOut(Card):
    card_name = "Snuff Out"

    def cast_actions(self, state):
        targets = [p.uid for p in state.battlefield
                   if p.is_creature_now and "B" not in p.card.colors]

        def effect(st, perm):
            if "B" in perm.card.colors:
                st.emit(f"Snuff Out: {perm.name} is black — illegal target")
                return
            st.emit(f"Snuff Out: destroy {perm.name}")
            st.leaves_battlefield(perm, "graveyard", reason="destroy")

        actions = targeted_instant_casts(
            self, state, targets, effect,
            cost=ManaCost(generic=3, pips=(("B", 1),)), tag="{3}{B}")
        # Alternative cost: pay 4 life if you control a Swamp.
        has_swamp = any(p.is_land and perm_has_subtype(p, ("Swamp",))
                        for p in state.battlefield)
        if has_swamp and state.life > 4:
            actions.extend(targeted_instant_casts(
                self, state, targets, effect,
                cost=ManaCost(), extra_life=4, tag="pay 4 life"))
        return actions
