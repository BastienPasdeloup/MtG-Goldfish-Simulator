"""Shorikai, Genesis Engine — {2}{W}{U} Legendary Artifact — Vehicle 8/8.
{1}, {T}: Draw two cards, then discard a card (branch), and create a 1/1 Pilot
token. Crew 8 is not modelled (vehicles never attack in this goldfish — a
Vehicle is not a creature unless crewed, and combat with crewing subsets is
out of scope)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Shorikai(Card):
    card_name = "Shorikai, Genesis Engine"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost):
            return []

        def fn(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return None
            p.tapped = True
            st.emit("Shorikai: {1}, {T} — draw 2, discard 1, make a Pilot")
            st.draw(2)
            st.make_token("Pilot", 1, 1, "Token Creature — Pilot")
            if not st.hand:
                return None
            branches = []
            seen: set[str] = set()
            for card in list(st.hand):
                if card.name in seen:
                    continue
                seen.add(card.name)
                b = st.clone()
                c = next(x for x in b.hand if x.name == card.name)
                b.hand.remove(c)
                b.to_graveyard(c)
                b.emit(f"discard {c.name}")
                branches.append(b)
            return branches

        return [CardAction("Shorikai: draw 2, discard 1, create Pilot", fn)]
