"""Barrowgoyf — {2}{B} Creature */1+*. Deathtouch, lifelink.
Power = number of card types among cards in all graveyards; toughness = that
plus 1. Combat damage: may mill that many; a creature milled this way may go
to hand (approximation: always mills, takes the first milled creature)."""
from __future__ import annotations

from .base import Card
from .registry import register

_TYPES = ("creature", "instant", "sorcery", "land", "artifact", "enchantment",
          "planeswalker", "battle")


def _gy_card_types(state) -> int:
    found = set()
    for c in state.graveyard:
        tl = c.type_line.lower()
        for t in _TYPES:
            if t in tl:
                found.add(t)
    return len(found)


@register
class Barrowgoyf(Card):
    card_name = "Barrowgoyf"

    def dynamic_power(self, state, perm):
        return _gy_card_types(state)

    def dynamic_toughness(self, state, perm):
        return _gy_card_types(state) + 1

    def on_combat_damage(self, state, perm, damage):
        milled = []
        for _ in range(min(damage, len(state.library))):
            card = state.library.pop(0)
            state.to_graveyard(card)
            milled.append(card)
        if milled:
            state.emit(f"Barrowgoyf: mill {len(milled)}")
            creature = next((c for c in milled if c.is_creature), None)
            if creature is not None:
                state.graveyard.remove(creature)
                state.hand.append(creature)
                state.emit(f"Barrowgoyf: {creature.name} to hand")
