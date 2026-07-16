"""Boggart Trawler // Boggart Bog — MDFC (Creature // Land).
Front (cast as a {2}{B} 3/1 Goblin): "when it enters, exile target player's
graveyard" — no effect against a phantom opponent.
Back (Boggart Bog, played as a land): as it enters, you may pay 3 life or it
enters tapped; {T}: Add {B}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class BoggartTrawler(Card):
    card_name = "Boggart Trawler // Boggart Bog"

    def mana_abilities_perm(self, state, perm):
        if perm.transformed:  # Boggart Bog
            return [ManaAbility(amount=1, choices=("B",))]
        return []

    def on_etb(self, state, permanent):
        if not permanent.transformed:
            state.emit("Boggart Trawler: no opponent graveyard to exile (goldfish)")

    def hand_actions(self, state):
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
                st.note_event("play_land", "Boggart Bog", card=card, is_land=True)
                perm = st.put_on_battlefield(card, fire_etb=False)
                perm.turn_flags["played_as_land"] = 1
                perm.transformed = True  # Boggart Bog
                perm.tapped = mode["tapped"]
                if mode["life"]:
                    st.life -= mode["life"]
                st.queue_entry_triggers([perm])
                st.emit(f"play land Boggart Bog ({mode['label']})")
                return None
            return fn

        return [CardAction(f"play land Boggart Bog ({m['label']})", make(m))
                for m in modes]
