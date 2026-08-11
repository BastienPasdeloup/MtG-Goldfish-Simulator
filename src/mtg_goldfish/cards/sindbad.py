"""Sindbad — {1}{U} Creature — Human 1/1.
{T}: Draw a card and reveal it. If it isn't a land card, discard it.

Digs for lands: {T} draws the top card and keeps it only if it's a land (otherwise
it's discarded)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Sindbad(Card):
    card_name = "Sindbad"

    def battlefield_actions(self, state, perm):
        if perm.tapped or perm.summoning_sick or not state.library:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or p.summoning_sick:
                return False
            p.tapped = True
            return True

        def resolve(st):
            before = len(st.hand)
            st.draw(1)
            if len(st.hand) > before:
                drawn = st.hand[-1]
                if not drawn.is_land:
                    st.discard(drawn)
                    st.emit(f"Sindbad: drew {drawn.name} (not a land) — discard it")
                else:
                    st.emit(f"Sindbad: drew {drawn.name} (a land) — keep it")
            return None

        return [CardAction.activated(
            "Sindbad: {T} — draw a card, keep only if a land",
            pay, resolve, source_name="Sindbad",
            ability_text="Draw a card; discard it unless it's a land")]
