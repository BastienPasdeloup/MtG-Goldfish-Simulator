"""Blightstep Pathway // Searstep Pathway — modal DFC land.
Play either face as your land drop (both enter untapped): Blightstep taps for
{B}, Searstep taps for {R}. The engine plays the front (Blightstep) via the
default land drop; the back (Searstep) via a custom hand action."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class BlightstepPathway(Card):
    card_name = "Blightstep Pathway // Searstep Pathway"

    def mana_abilities_perm(self, state, perm):
        color = "R" if perm.transformed else "B"
        return [ManaAbility(amount=1, choices=(color,))]

    def hand_actions(self, state):
        if state.lands_played_this_turn >= state.max_land_drops():
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or st.lands_played_this_turn >= st.max_land_drops():
                return None
            st.hand.remove(card)
            st.lands_played_this_turn += 1
            st.note_event("play_land", "Searstep Pathway", card=card, is_land=True)
            perm = st.put_on_battlefield(card, fire_etb=False, transformed=True)  # Searstep Pathway
            perm.turn_flags["played_as_land"] = 1
            st.queue_entry_triggers([perm])
            st.emit("play land Searstep Pathway")
            return None

        return [CardAction("play land Searstep Pathway", fn)]
