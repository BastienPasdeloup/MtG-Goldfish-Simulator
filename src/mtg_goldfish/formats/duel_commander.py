"""Duel Commander: 1v1 Commander. 20 life, 100-card singleton, one commander.

We goldfish a single player, so opponent-facing rules (commander damage, etc.)
are not modelled; what matters here is setup and deck validation.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..deck.models import Deck, DeckBoard
from .base import Format

_BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}


@dataclass(frozen=True)
class DuelCommander(Format):
    def validate(self, deck: Deck) -> list[str]:
        problems: list[str] = []
        if not deck.commanders:
            problems.append(
                "Duel Commander requires exactly one commander (none found)."
            )
        elif len(deck.commanders) > 2:
            problems.append("Too many commanders (a partner pair is the maximum).")

        seen: dict[str, int] = {}
        for entry in deck.entries:
            if entry.board in (DeckBoard.MAINBOARD, DeckBoard.COMMANDER):
                seen[entry.card.name] = seen.get(entry.card.name, 0) + entry.quantity
        for name, count in seen.items():
            if count > 1 and name not in _BASICS:
                problems.append(f"Singleton violation: {count}× {name!r}.")
        return problems


DUEL_COMMANDER = DuelCommander(
    id="duel_commander",
    name="Duel Commander",
    starting_life=20,
    starting_hand_size=7,
    deck_size=100,
    singleton=True,
    uses_commander=True,
    uses_companion=True,
)
