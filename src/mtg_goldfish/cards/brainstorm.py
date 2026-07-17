"""Brainstorm — {U} Instant. Draw three cards, then put two cards from your
hand on top of your library in any order (every ordered pair is a branch)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Brainstorm(Card):
    card_name = "Brainstorm"

    def on_resolve(self, state):
        state.draw(3)
        state.emit(f"Brainstorm: draw 3 ({len(state.hand)} in hand)")
        n = len(state.hand)
        if n <= 2:
            # Put the whole hand back.
            while state.hand:
                card = state.hand.pop()
                state.library.insert(0, card)
                state.mark_known_in_library(card)  # player knows it's on top
            state.emit("Brainstorm: put hand back on top")
            return None

        seen: set[tuple[str, str]] = set()
        branches = []
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                key = (state.hand[i].name, state.hand[j].name)
                if key in seen:
                    continue
                seen.add(key)
                b = state.clone()
                first = b.hand[i]
                second = b.hand[j]
                b.hand.remove(first)
                b.hand.remove(second)
                # `second` ends up on top (drawn first next).
                b.library.insert(0, first)
                b.library.insert(0, second)
                b.mark_known_in_library(first, second)  # player knows the top two
                b.emit(f"Brainstorm: put back {second.name} (top), {first.name}")
                branches.append(b)
        return branches
