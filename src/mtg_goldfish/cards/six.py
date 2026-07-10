"""Six — {2}{G} Legendary Creature — Treefolk 2/4, reach.
Whenever Six attacks, mill three cards; you may put a land card from among
them into your hand (deterministic: keep the first land milled — attack
triggers can't branch). Retrace (casting permanents from the graveyard by
discarding a land) is not modelled — a documented approximation."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Six(Card):
    card_name = "Six"

    def on_attack(self, state, perm):
        top = state.library[:3]
        kept = next((c for c in top if c.is_land), None)
        for c in top:
            state.library.remove(c)
            if c is kept:
                state.hand.append(c)
            else:
                state.to_graveyard(c)
        state.emit(f"Six attacks: mill 3, keep {kept.name if kept else 'no land'}")
