"""Shorikai, Genesis Engine — {2}{W}{U} Legendary Artifact — Vehicle 8/8.
{1}, {T}: Draw two cards, then discard a card (branch), and create a 1/1 Pilot
token. Crew 8: tap creatures with total power >= 8 to make it an 8/8 artifact
creature until end of turn (each activation also makes a Pilot, so it can
build its own crew over several turns)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import crew_action
from .base import Card, CardAction
from .registry import register


@register
class Shorikai(Card):
    card_name = "Shorikai, Genesis Engine"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        acts = crew_action(self, state, perm, 8)
        cost = ManaCost(generic=1)
        if perm.tapped or not can_afford(state, cost):
            return acts

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
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

        return acts + [CardAction.activated(
            "Shorikai: draw 2, discard 1, create Pilot",
            pay,
            resolve,
            source_name="Shorikai, Genesis Engine",
            ability_text="Draw 2, discard 1, create a Pilot token",
        )]
