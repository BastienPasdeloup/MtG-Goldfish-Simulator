"""Malcolm, Alluring Scoundrel — {1}{U} 2/1 flash, flying.
Combat damage: chorus counter, then draw a card and discard a card.
Approximations (combat triggers cannot branch in this engine): the discard is
deterministic (highest mana value card), and the 4+-chorus free cast of the
discarded card is not modelled."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MalcolmAlluringScoundrel(Card):
    card_name = "Malcolm, Alluring Scoundrel"

    def on_combat_damage(self, state, perm, damage):
        perm.counters["chorus"] = perm.counters.get("chorus", 0) + 1
        state.emit(f"Malcolm: chorus counter ({perm.counters['chorus']}), draw then discard")
        state.draw(1)
        if state.hand:
            worst = max(state.hand, key=lambda c: c.cmc)
            state.hand.remove(worst)
            state.to_graveyard(worst)
            state.emit(f"Malcolm: discard {worst.name}")
