"""Command Beacon — Land.
{T}: Add {C}. {T}, Sacrifice: put your commander into your hand from the
command zone (it can then be cast for its printed cost, without tax)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class CommandBeacon(Card):
    card_name = "Command Beacon"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped or not state.command_zone:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not st.command_zone:
                return False
            p.tapped = True
            st.leaves_battlefield(p, "graveyard")
            return True

        def resolve(st):
            if not st.command_zone:
                return None
            commander = st.command_zone.pop(0)
            st.hand.append(commander)
            st.emit(f"Command Beacon: sacrifice — {commander.name} to hand")
            return None

        return [CardAction.activated(
            "Command Beacon: commander to hand",
            pay,
            resolve,
            source_name="Command Beacon",
            ability_text="Put your commander into your hand",
        )]
