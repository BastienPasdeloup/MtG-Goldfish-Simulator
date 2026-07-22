"""Clearwater Pathway // Murkwater Pathway — modal DFC land.
Play either face as your land drop (both untapped): Clearwater taps for {U},
Murkwater taps for {B}. The engine plays the front (Clearwater) as the default
land drop; the back (Murkwater) via a custom hand action."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class ClearwaterPathway(Card):
    card_name = "Clearwater Pathway // Murkwater Pathway"

    def mana_abilities_perm(self, state, perm):
        return [ManaAbility(amount=1, choices=("B" if perm.transformed else "U",))]

    def hand_actions(self, state):
        if state.lands_played_this_turn >= state.max_land_drops():
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or st.lands_played_this_turn >= st.max_land_drops():
                return None
            st.hand.remove(card)
            st.lands_played_this_turn += 1
            st.note_event("play_land", "Murkwater Pathway", card=card, is_land=True)
            perm = st.put_on_battlefield(card, fire_etb=False, transformed=True)  # Murkwater Pathway
            perm.turn_flags["played_as_land"] = 1
            st.queue_entry_triggers([perm])
            st.emit("play land Murkwater Pathway")
            return None

        return [CardAction("play land Murkwater Pathway", fn)]
