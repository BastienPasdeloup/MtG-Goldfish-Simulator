"""Bomat Courier — {1} Artifact Creature 1/1, haste.
Whenever it attacks, exile the top card of your library face down.
{R}, Discard your hand, Sacrifice this creature: Put all cards exiled with this
creature into their owners' hands."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class BomatCourier(Card):
    card_name = "Bomat Courier"
    exiles_cards = True

    def on_attack(self, state, perm):
        if state.library:
            card = state.library.pop(0)
            perm.exiled_with.append(card)
            state.emit(f"Bomat Courier: exile top card face down "
                       f"({len(perm.exiled_with)} stored)")

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("R", 1),))
        if not can_afford(state, cost):
            return []
        exiled = list(perm.exiled_with)

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return False
            for c in list(st.hand):
                st.discard(c)
            st.emit("Bomat Courier: discard hand, sacrifice")
            st.leaves_battlefield(p, "graveyard", reason="sacrifice")
            return True

        def resolve(st):
            for c in exiled:
                st.hand.append(c)
            st.emit(f"Bomat Courier: draw {len(exiled)} exiled cards")
            return None

        return [CardAction.activated(
            f"Bomat Courier: {{R}}, discard hand, sac → draw {len(exiled)}",
            pay, resolve,
            source_name="Bomat Courier",
            ability_text="Put all cards exiled with this creature into your hand")]
