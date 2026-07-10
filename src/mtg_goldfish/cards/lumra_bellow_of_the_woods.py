"""Lumra, Bellow of the Woods — {4}{G}{G} Legendary Creature — Elemental Bear.
Vigilance, reach. Power/toughness each equal to the number of lands you
control. ETB: mill four cards, then return all land cards from your graveyard
to the battlefield tapped."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class LumraBellowOfTheWoods(Card):
    card_name = "Lumra, Bellow of the Woods"

    def dynamic_power(self, state, perm):
        return sum(1 for p in state.battlefield if "land" in p.type_line.lower())

    def dynamic_toughness(self, state, perm):
        return sum(1 for p in state.battlefield if "land" in p.type_line.lower())

    def on_etb(self, state, permanent):
        state.mill(4)
        lands = [c for c in state.graveyard if c.is_land]
        for card in lands:
            state.graveyard.remove(card)
            state.put_on_battlefield(card, tapped=True)
        if lands:
            state.emit(f"Lumra: return {len(lands)} land(s) from graveyard tapped")
