"""Amulet of Kroog — {2} Artifact.
{2}, {T}: Prevent the next 1 damage that would be dealt to any target this turn.

Adds a colourless prevention shield against your self-damage (the modelable
"any target" is you — Ankh, Mana Vault, Copper Tablet, etc.)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class AmuletOfKroog(Card):
    card_name = "Amulet of Kroog"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={p.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.prevent_shields.append((1, None))
            st.emit("Amulet of Kroog: prevent the next 1 damage to you this turn")
            return None

        return [CardAction.activated(
            "Amulet of Kroog: {2}, {T} — prevent the next 1 damage",
            pay, resolve, source_name="Amulet of Kroog",
            ability_text="Prevent the next 1 damage this turn")]
