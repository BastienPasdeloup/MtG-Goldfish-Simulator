"""Feldon's Cane — {1} Artifact.
{T}, Exile this artifact: Shuffle your graveyard into your library.

Recycles the graveyard back into the deck (anti-decking / re-draw fuel). The
per-game shuffle model randomises the new library order."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class FeldonsCane(Card):
    card_name = "Feldon's Cane"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            live = st.find_permanent(perm.uid)
            if live is None or live.tapped:
                return False
            live.tapped = True
            st.leaves_battlefield(live, "exile", reason=None)
            return True

        def resolve(st):
            n = len(st.graveyard)
            st.library.extend(st.graveyard)
            st.graveyard.clear()
            st.shuffle_library()
            st.emit(f"Feldon's Cane: shuffle {n} card(s) from graveyard into library")
            return None

        return [CardAction.activated(
            "Feldon's Cane: {T}, exile — shuffle graveyard into library",
            pay, resolve, source_name="Feldon's Cane",
            ability_text="Shuffle your graveyard into your library")]
