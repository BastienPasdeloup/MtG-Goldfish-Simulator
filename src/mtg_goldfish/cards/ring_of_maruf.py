"""Ring of Ma'rûf — {5} Artifact.
{5}, {T}, Exile this artifact: The next time you would draw a card this turn,
instead put a card you own from outside the game into your hand.

Wish effect: {5}, {T}, and exile the Ring to put a card from your SIDEBOARD (the
deck's "outside the game" pool, `state.sideboard`) into your hand — one branch per
distinct sideboard card. The "next draw replacement" timing is simplified to
putting the card into hand immediately. Only offered when a sideboard is loaded."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class RingOfMaruf(Card):
    card_name = "Ring of Ma'rûf"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=5)
        if perm.tapped or not state.sideboard or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            me = st.find_permanent(perm.uid)
            if me is None or me.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            me.tapped = True
            st.leaves_battlefield(me, "exile", reason="exile")
            return True

        def resolve(st):
            seen: set[str] = set()
            opts = []
            for c in st.sideboard:
                if c.name not in seen:
                    seen.add(c.name)
                    opts.append(c.name)

            def fn(s, name):
                card = next((c for c in s.sideboard if c.name == name), None)
                if card is not None:
                    s.sideboard.remove(card)
                    s.hand.append(card)
                    s.emit(f"Ring of Ma'rûf: put {name} from outside the game into your hand")
                return None

            return st.settle(branch_over(st, opts, fn))

        return [CardAction.activated(
            "Ring of Ma'rûf: {5}, {T}, Exile — get a card from outside the game",
            pay, resolve, source_name="Ring of Ma'rûf",
            ability_text="Put a card you own from outside the game into your hand")]
