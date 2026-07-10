"""Horizon of Progress — Land.
{T}, Pay 1 life: add one mana of any type a land you control could produce
(approximated as any identity color). {3}, {T}: put a land from your hand
onto the battlefield tapped (branch). {1}, {T}, Sacrifice: draw a card."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ._common import any_identity_color, enter_battlefield
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
                def pay_put(st, nm=name):
                    p = st.find_permanent(perm.uid)
                    card = next((c for c in st.hand if c.name == nm), None)
                    if (p is None or p.tapped or card is None
                            or not pay_cost(st, ManaCost(generic=3), exclude_uids={perm.uid})):
                        return False
                    p.tapped = True
                    return True

                def resolve_put(st, nm=name):
                    card = next((c for c in st.hand if c.name == nm), None)
                    if card is None:
                        return None
                    st.hand.remove(card)
                    enter_battlefield(
                        st,
                        card,
                        tapped=True,
                        announce=f"Horizon of Progress: put {nm} onto the battlefield tapped",
                    )
                    return None
                acts.append(CardAction.activated(
                    f"Horizon of Progress: put {name} tapped",
                    pay_put,
                    resolve_put,
                    source_name="Horizon of Progress",
                    ability_text=f"Put {name} onto the battlefield tapped",
                ))

        # {1}, {T}, Sacrifice: draw a card.
        if can_afford(state, ManaCost(generic=1), exclude_uids={perm.uid}):
            def pay_draw(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, ManaCost(generic=1), exclude_uids={perm.uid}):
                    return False
                st.leaves_battlefield(p, "graveyard")
                return True

            def resolve_draw(st):
                st.emit("Horizon of Progress: sacrifice — draw a card")
                st.draw(1)
                return None
            acts.append(CardAction.activated(
                "Horizon of Progress: sacrifice, draw",
                pay_draw,
                resolve_draw,
                source_name="Horizon of Progress",
                ability_text="Draw a card",
            ))

        return acts
