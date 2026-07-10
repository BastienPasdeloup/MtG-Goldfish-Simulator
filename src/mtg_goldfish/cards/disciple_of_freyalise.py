"""Disciple of Freyalise // Garden of Freyalise — Creature // Land (MDFC).
The land face is played via a custom hand action (the engine's type parser
sees the front face, a creature): pay 3 life untapped / tapped; {T}: Add {G}.
The front creature is castable as a vanilla 3/3 for {3}{G}{G}{G}.
Approximation: the front's optional sacrifice-for-value ETB is skipped
(sacrificing a real creature is rarely right in a goldfish)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class DiscipleOfFreyalise(Card):
    card_name = "Disciple of Freyalise // Garden of Freyalise"

    def mana_abilities_perm(self, state, perm):
        if perm.transformed:  # Garden of Freyalise
            return [ManaAbility(amount=1, choices=("G",))]
        return []

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
                perm = st.put_on_battlefield(card, fire_etb=False)
                perm.transformed = True  # it is Garden of Freyalise
                perm.tapped = mode["tapped"]
                if mode["life"]:
                    st.life -= mode["life"]
                st.fire_other_etb(perm)
                st.emit(f"play land Garden of Freyalise ({mode['label']})")
                return None
            return fn

        return [CardAction(f"play land Garden of Freyalise ({m['label']})", make(m))
                for m in modes]
