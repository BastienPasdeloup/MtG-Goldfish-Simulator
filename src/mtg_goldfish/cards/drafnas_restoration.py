"""Drafna's Restoration — {U} Sorcery.
Put any number of target artifact cards from target player's graveyard on top of
their library in any order.

Targets you: puts every artifact card in your graveyard on top of your library
(re-draw fuel)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DrafnasRestoration(Card):
    card_name = "Drafna's Restoration"

    def on_resolve(self, state):
        arts = [c for c in list(state.graveyard) if c.is_artifact]
        if not arts:
            return None
        for c in arts:
            state.graveyard.remove(c)
        # Put them on top of the library (front = next to draw).
        state.library[:0] = arts
        state.mark_known_in_library(*arts)
        state.emit(f"Drafna's Restoration: put {len(arts)} artifact card(s) on top of library")
        return None
