"""Claim // Fame — split (aftermath).
Claim ({B} sorcery): Return target creature card with mana value 2 or less from
your graveyard to the battlefield.
Fame ({1}{R} sorcery, aftermath): cast only from your graveyard, then exile it —
target creature gets +2/+0 and gains haste until end of turn."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class ClaimFame(Card):
    card_name = "Claim // Fame"

    def cast_cost(self, state):
        return ManaCost(pips=(("B", 1),))  # Claim (front half)

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        targets = sorted({c.name for c in state.graveyard
                          if c.is_creature and c.cmc <= 2})
        if not targets or not can_afford(state, cost):
            return []

        def make(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)  # Claim to graveyard; Fame usable later
                c = next((x for x in st.graveyard
                          if x.name == name and x.is_creature), None)
                if c is None:
                    return None
                st.leave_graveyard(c)
                enter_battlefield(st, c, announce=f"Claim: return {name} to battlefield")
                return None
            return fn

        return [CardAction(f"cast Claim → {n}", make(n)) for n in targets]

    def graveyard_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("R", 1),))
        creatures = {p.name: p.uid for p in state.battlefield if p.is_creature_now}
        if not creatures or not can_afford(state, cost):
            return []

        def make(uid):
            def fn(st):
                card = next((c for c in st.graveyard if c.name == self.card_name), None)
                p = st.find_permanent(uid)
                if card is None or p is None or not pay_cost(st, cost):
                    return None
                st.graveyard.remove(card)
                st.exile.append(card)  # aftermath exiles
                p.temp_power += 2
                p.temp_keywords.add("haste")
                st.emit(f"Fame: {p.name} gets +2/+0 and haste")
                return None
            return fn

        # "cast " label → CardAction.apply pays + resolves in one step (fn).
        return [CardAction(f"cast Fame (aftermath) → {name}", make(uid))
                for name, uid in creatures.items()]
