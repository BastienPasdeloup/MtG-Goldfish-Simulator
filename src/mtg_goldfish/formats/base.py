"""Format definitions.

A `Format` captures the deck-construction and game-setup rules the simulator
needs: starting life/hand, whether there are commanders/companions, and how to
validate a decklist. New formats register themselves in `registry.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..deck.models import Deck


@dataclass(frozen=True)
class Format:
    id: str
    name: str
    starting_life: int = 20
    starting_hand_size: int = 7
    deck_size: int = 60
    singleton: bool = False
    uses_commander: bool = False
    uses_companion: bool = True

    def validate(self, deck: Deck) -> list[str]:
        """Return a list of human-readable rule violations (empty == legal)."""
        problems: list[str] = []
        if self.uses_commander and not deck.commanders:
            problems.append("This format requires a commander, but none was found.")
        return problems
