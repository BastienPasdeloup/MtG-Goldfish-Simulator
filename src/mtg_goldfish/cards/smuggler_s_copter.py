"""Smuggler's Copter — {2} Artifact — Vehicle 3/3, flying, crew 1.
Crew 1 (tap creatures with total power >= 1) makes it a 3/3 flying artifact
creature until end of turn, so it can attack. Whenever it attacks you may draw a
card, then discard a card (loot) — modelled as a branch: don't loot, or draw one
and branch over which card to discard."""
from __future__ import annotations

from ._common import crew_action
from .base import Card
from .registry import register


@register
class SmugglersCopter(Card):
    card_name = "Smuggler's Copter"

    def battlefield_actions(self, state, perm):
        return crew_action(self, state, perm, 1, keywords=("flying",))

    def on_attack(self, state, perm):
        from ._common import branch_over

        # "you may draw a card. If you do, discard a card." -> don't loot, or
        # draw one then branch over which card to discard.
        def fn(st, loot):
            if not loot:
                st.emit("Smuggler's Copter: no loot")
                return None
            st.draw(1)
            if not st.hand:
                return None
            seen: set[str] = set()
            branches = []
            for card in list(st.hand):
                if card.name in seen:
                    continue
                seen.add(card.name)
                b = st.clone()
                c = next(x for x in b.hand if x.name == card.name)
                b.hand.remove(c)
                b.to_graveyard(c)
                b.emit(f"Smuggler's Copter loot: discard {c.name}")
                branches.append(b)
            return branches

        return branch_over(state, [False, True], fn)
