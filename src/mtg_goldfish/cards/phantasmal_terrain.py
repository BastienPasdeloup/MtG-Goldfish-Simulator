"""Phantasmal Terrain — {U}{U} Enchantment — Aura. Enchant land.
As this Aura enters, choose a basic land type. Enchanted land is the chosen type.

Retypes one of your lands to a basic type of your choice — modelled as a mana
override so the land taps for the chosen colour (real fixing). Branches over
(land × the five basic types)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register

_BASICS = [("Plains", "W"), ("Island", "U"), ("Swamp", "B"),
           ("Mountain", "R"), ("Forest", "G")]


@register
class PhantasmalTerrain(Card):
    card_name = "Phantasmal Terrain"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford

        if not can_afford(state, self.mana_cost):
            return []
        lands: dict[str, int] = {}
        for p in state.battlefield:
            if p.is_land and p.name not in lands:
                lands[p.name] = p.uid

        acts = []
        for lname, uid in lands.items():
            for basic, color in _BASICS:
                def make(uid=uid, basic=basic, color=color):
                    def fn(st):
                        card = next((c for c in st.hand if c.name == self.card_name), None)
                        host = st.find_permanent(uid)
                        if card is None or host is None or not begin_cast(st, card, self.mana_cost):
                            return None
                        if card in st.stack:
                            st.stack.remove(card)
                        aura = st.put_on_battlefield(card, fire_etb=False)
                        aura.attached_to = host.uid
                        host.mana_override = color
                        st.emit(f"Phantasmal Terrain: {host.name} becomes a {basic}")
                        return None
                    return fn

                acts.append(CardAction(
                    f"cast Phantasmal Terrain → {lname} becomes {basic}", make()))
        return acts

    def on_leave(self, state, perm):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.mana_override = None
