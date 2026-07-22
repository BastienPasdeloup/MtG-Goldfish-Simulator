"""Waterlogged Teachings // Inundated Archive — MDFC.
Front (Waterlogged Teachings, {3}{U/B} Instant): search your library for an
instant card or a card with flash, put it into your hand, then shuffle.
Back (Inundated Archive, Land): enters tapped; {T}: Add {U} or {B}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class WaterloggedTeachings(Card):
    card_name = "Waterlogged Teachings // Inundated Archive"

    def mana_abilities_perm(self, state, perm):
        if perm.transformed:  # Inundated Archive
            return [ManaAbility(amount=1, choices=("U", "B"))]
        return []

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)  # {3}{U/B} -> {3}{U}
        if not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            targets = st.search_library(
                lambda c: c.is_instant or "flash" in [k.lower() for k in c.keywords])
            if not targets:
                st.shuffle_library()
                st.emit("Waterlogged Teachings: no instant/flash card found")
                return None

            def pick(s, name):
                c = next((x for x in s.library if x.name == name), None)
                if c is not None:
                    s.take_from_library(c)
                    s.hand.append(c)
                s.shuffle_library()
                s.emit(f"Waterlogged Teachings: {name} to hand — shuffle")
                return None

            return branch_over(st, [t.name for t in targets], pick)

        return [CardAction("cast Waterlogged Teachings", fn)]

    def hand_actions(self, state):
        # Back face: play Inundated Archive as a land (enters tapped).
        if state.lands_played_this_turn >= state.max_land_drops():
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or st.lands_played_this_turn >= st.max_land_drops():
                return None
            st.hand.remove(card)
            st.lands_played_this_turn += 1
            st.note_event("play_land", "Inundated Archive", card=card, is_land=True)
            perm = st.put_on_battlefield(card, fire_etb=False, transformed=True)  # Inundated Archive
            perm.turn_flags["played_as_land"] = 1
            perm.tapped = True
            st.queue_entry_triggers([perm])
            st.emit("play land Inundated Archive (tapped)")
            return None

        return [CardAction("play land Inundated Archive (tapped)", fn)]
