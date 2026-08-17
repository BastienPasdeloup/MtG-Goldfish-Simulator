"""Millstone — {2} Artifact.
{2}, {T}: Target player mills two cards.

The useful target in a goldfish is YOU (self-mill for graveyard synergies);
milling the phantom opponent is a no-op, so only the self-mill is offered."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Millstone(Card):
    card_name = "Millstone"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            live = st.find_permanent(perm.uid)
            if live is None or live.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            live.tapped = True
            return True

        def resolve(st):
            st.mill(2)
            st.emit("Millstone: mill 2 (yourself)")
            return None

        return [CardAction.activated(
            "Millstone: {2}, {T} — mill 2 (yourself)",
            pay, resolve, source_name="Millstone",
            ability_text="Target player mills two cards")]
