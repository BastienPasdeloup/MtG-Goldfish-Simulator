"""Talon Gates of Madara — Land — Gate.
{T}: Add {C}. {1}, {T}: add one mana of any color (battlefield action).
{4}: put this card from your hand onto the battlefield (not a land drop).
The phase-out ETB targets a creature — no-op without an opponent."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ._common import any_identity_color
from .base import Card, CardAction
from .registry import register


@register
class TalonGatesOfMadara(Card):
    card_name = "Talon Gates of Madara"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def hand_actions(self, state):
        cost = ManaCost(generic=4)
        if not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, cost):
                return False
            return True

        def resolve(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None:
                return None
            st.hand.remove(card)
            st.put_on_battlefield(card)
            st.emit("Talon Gates of Madara: {4} — onto the battlefield (no land drop)")
            return None

        return [CardAction.activated(
            "Talon Gates of Madara: {4}, put onto battlefield",
            pay,
            resolve,
            source_name="Talon Gates of Madara",
            ability_text="Put Talon Gates of Madara onto the battlefield",
        )]

    def battlefield_actions(self, state, perm):
        # Taps for this ability, so its own {T}:{C} can't help pay the {1}.
        if perm.tapped or not can_afford(state, ManaCost(generic=1), exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, ManaCost(generic=1), exclude_uids={perm.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            color = any_identity_color(st)[0]
            st.mana_pool.add(color, 1)
            st.emit(f"Talon Gates of Madara: {{1}}, {{T}} — add {{{color}}}")
            return None

        return [CardAction.activated(
            "Talon Gates of Madara: {1}, {T} — any color",
            pay,
            resolve,
            source_name="Talon Gates of Madara",
            ability_text="Add one mana of any color",
        )]
