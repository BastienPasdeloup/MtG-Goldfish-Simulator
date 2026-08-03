"""Griselbrand — {4}{B}{B}{B}{B} 7/7 Flying, lifelink. Pay 7 life: Draw seven
cards (a repeatable battlefield activation)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class Griselbrand(Card):
    card_name = "Griselbrand"

    def battlefield_actions(self, state, perm):
        if state.life <= 7:
            return []

        def pay(st):
            if st.life <= 7:
                return False
            st.life -= 7
            return True

        def resolve(st):
            st.draw(7)
            st.emit(f"Griselbrand: pay 7 life, draw seven ({len(st.hand)} in hand, "
                    f"life {st.life})")
            return None

        return [CardAction.activated(
            "Griselbrand: pay 7 life, draw 7", pay, resolve,
            source_name="Griselbrand", ability_text="Pay 7 life: Draw seven cards")]
