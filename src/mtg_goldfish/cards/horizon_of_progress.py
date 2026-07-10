"""Horizon of Progress — Land.
{T}, Pay 1 life: add one mana of any type a land you control could produce
(approximated as any identity color). {3}, {T}: put a land from your hand
onto the battlefield tapped (branch). {1}, {T}, Sacrifice: draw a card."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class HorizonOfProgress(Card):
    card_name = "Horizon of Progress"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state), life_cost=1)]

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        acts = []

        # {3}, {T}: put a land card from hand onto the battlefield tapped.
        # Taps for the ability, so it can't help pay its own cost.
        if can_afford(state, ManaCost(generic=3), exclude_uids={perm.uid}):
            for name in sorted({c.name for c in state.hand if c.is_land}):
                def put(st, nm=name):
                    p = st.find_permanent(perm.uid)
                    card = next((c for c in st.hand if c.name == nm), None)
                    if (p is None or p.tapped or card is None
                            or not pay_cost(st, ManaCost(generic=3), exclude_uids={perm.uid})):
                        return None
                    p.tapped = True
                    st.hand.remove(card)
                    st.put_on_battlefield(card, tapped=True)
                    st.emit(f"Horizon of Progress: put {nm} onto the battlefield tapped")
                    return None
                acts.append(CardAction(f"Horizon of Progress: put {name} tapped", put))

        # {1}, {T}, Sacrifice: draw a card.
        if can_afford(state, ManaCost(generic=1), exclude_uids={perm.uid}):
            def draw(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, ManaCost(generic=1), exclude_uids={perm.uid}):
                    return None
                st.leaves_battlefield(p, "graveyard")
                st.emit("Horizon of Progress: sacrifice — draw a card")
                st.draw(1)
                return None
            acts.append(CardAction("Horizon of Progress: sacrifice, draw", draw))

        return acts
