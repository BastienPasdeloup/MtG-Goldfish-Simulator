"""Mount Doom — Legendary Land.
{T}, Pay 1 life: Add {B} or {R}.
{1}{B}{R}, {T}: Mount Doom deals 1 damage to each opponent.
The third ability (sacrifice Mount Doom + a legendary artifact to wrath) is a
symmetric board-destruction that only hurts your own board in a goldfish, so it
is not modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class MountDoom(Card):
    card_name = "Mount Doom"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B", "R"), life_cost=1)]

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1, pips=(("B", 1), ("R", 1)))
        if perm.tapped or not can_afford(state, cost):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, cost):
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.opponent_life -= 1
            st.note_crime()
            st.emit(f"Mount Doom: 1 damage to opponent ({st.opponent_life})")
            return None

        return [CardAction.activated(
            "Mount Doom: 1 damage to each opponent",
            pay,
            resolve,
            source_name="Mount Doom",
            ability_text="Deal 1 damage to each opponent",
        )]
