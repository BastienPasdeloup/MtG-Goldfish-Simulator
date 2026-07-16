"""Sundering Eruption // Volcanic Fissure — modal DFC.
Front (Sundering Eruption, {2}{R} sorcery): Destroy target land; its controller
may search for a basic land onto the battlefield tapped, then shuffle. (In a
goldfish the only land targets are your own.)
Back (Volcanic Fissure, land): as it enters, pay 3 life or it enters tapped;
{T}: Add {R}."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import branch_over, enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class SunderingEruption(Card):
    card_name = "Sundering Eruption // Volcanic Fissure"

    def cast_cost(self, state):
        return ManaCost(generic=2, pips=(("R", 1),))  # Sundering Eruption (front)

    def is_castable(self, state):
        return any(p.is_land for p in state.battlefield)

    def mana_abilities_perm(self, state, perm):
        if perm.transformed:  # Volcanic Fissure
            return [ManaAbility(amount=1, choices=("R",))]
        return []

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        lands = {p.name: p.uid for p in state.battlefield if p.is_land}
        if not lands or not can_afford(state, cost):
            return []

        def make(uid):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                target = st.find_permanent(uid)
                if card is None or target is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                st.emit(f"Sundering Eruption: destroy {target.name}")
                st.leaves_battlefield(target, "graveyard", reason="destroy")
                basics = sorted({c.name for c in st.library
                                 if c.is_land and "basic" in c.type_line.lower()})
                options = ["(no fetch)"] + basics

                def fetch(s, name):
                    if name != "(no fetch)":
                        c = next((x for x in s.library if x.name == name), None)
                        if c is not None:
                            s.take_from_library(c)
                            s.shuffle_library()
                            enter_battlefield(s, c, tapped=True,
                                              announce=f"Sundering Eruption: fetch {name} tapped — shuffle")
                    return None

                return branch_over(st, options, fetch)
            return fn

        return [CardAction(f"cast Sundering Eruption → destroy {name}", make(uid))
                for name, uid in lands.items()]

    def hand_actions(self, state):
        # Back face: play Volcanic Fissure as a land.
        if state.lands_played_this_turn >= state.max_land_drops():
            return []
        modes = []
        if state.life > 3:
            modes.append({"label": "pay 3 life, untapped", "tapped": False, "life": 3})
        modes.append({"label": "tapped", "tapped": True, "life": 0})

        def make(mode):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or st.lands_played_this_turn >= st.max_land_drops():
                    return None
                if mode["life"] and st.life <= mode["life"]:
                    return None
                st.hand.remove(card)
                st.lands_played_this_turn += 1
                st.note_event("play_land", "Volcanic Fissure", card=card, is_land=True)
                perm = st.put_on_battlefield(card, fire_etb=False)
                perm.turn_flags["played_as_land"] = 1
                perm.transformed = True
                perm.tapped = mode["tapped"]
                if mode["life"]:
                    st.life -= mode["life"]
                st.queue_entry_triggers([perm])
                st.emit(f"play land Volcanic Fissure ({mode['label']})")
                return None
            return fn

        return [CardAction(f"play land Volcanic Fissure ({m['label']})", make(m))
                for m in modes]
