"""Takenuma, Abandoned Mire — Legendary Land. {T}: Add {B}.
Channel — {3}{B}, Discard this card: Mill three cards, then return a creature or
planeswalker card from your graveyard to your hand ({1} less to activate per
legendary creature you control)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class TakenumaAbandonedMire(Card):
    card_name = "Takenuma, Abandoned Mire"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        legends = sum(1 for p in state.battlefield
                      if p.is_creature_now and "legendary" in p.type_line.lower())
        cost = ManaCost(generic=max(0, 3 - legends), pips=(("B", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, cost):
                return False
            st.hand.remove(card)
            st.to_graveyard(card)
            st.emit("channel Takenuma (discard)")
            return True

        def resolve(st):
            st.mill(3)
            targets = {c.name: c for c in st.graveyard
                       if c.is_creature or "planeswalker" in c.type_line.lower()}
            if not targets:
                st.emit("channel Takenuma: nothing to return")
                return None

            def fn(s, name):
                c = next((x for x in s.graveyard if x.name == name), None)
                if c is None:
                    return None
                s.graveyard.remove(c)
                s.hand.append(c)
                s.emit(f"channel Takenuma: return {name} to hand")
                return None

            return branch_over(st, list(targets), fn)

        return [CardAction.activated(
            "channel Takenuma: mill 3, return a creature/planeswalker",
            pay,
            resolve,
            source_name=self.card_name,
            ability_text="Channel — mill three, return a creature/planeswalker",
        )]
