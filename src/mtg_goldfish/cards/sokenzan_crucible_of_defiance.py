"""Sokenzan, Crucible of Defiance — Legendary Land. {T}: Add {R}.
Channel — {3}{R}, Discard this card: Create two 1/1 Spirit tokens with haste
until end of turn ({1} less to activate per legendary creature you control)."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class SokenzanCrucibleOfDefiance(Card):
    card_name = "Sokenzan, Crucible of Defiance"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("R",))]

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        legends = sum(1 for p in state.battlefield
                      if p.is_creature_now and "legendary" in p.type_line.lower())
        cost = ManaCost(generic=max(0, 3 - legends), pips=(("R", 1),))
        if not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, cost):
                return False
            st.hand.remove(card)
            st.to_graveyard(card)
            st.emit("channel Sokenzan (discard)")
            return True

        def resolve(st):
            for _ in range(2):
                tok = st.make_token("Spirit", 1, 1, "Creature — Spirit")
                tok.summoning_sick = False
                tok.temp_keywords.add("haste")
            st.emit("channel Sokenzan: two 1/1 Spirits with haste")
            return None

        return [CardAction.activated(
            "channel Sokenzan: two 1/1 Spirits (haste)",
            pay,
            resolve,
            source_name=self.card_name,
            ability_text="Channel — create two hasty 1/1 Spirit tokens",
        )]
