"""Balance — {1}{W} Sorcery.
Each player keeps lands/creatures equal to the fewest any player controls and
sacrifices the rest; each player discards down to the fewest cards in hand.

Against a do-nothing goldfish opponent (0 lands, 0 creatures, 0 cards) the
"fewest" is 0, so Balance makes YOU sacrifice all your lands and creatures and
discard your whole hand — the faithful (and rarely useful) goldfish result."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Balance(Card):
    card_name = "Balance"

    def on_resolve(self, state):
        lands = [p for p in state.battlefield if p.is_land]
        creatures = [p for p in state.battlefield if p.is_creature_now]
        for p in lands + creatures:
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        n_hand = len(state.hand)
        for c in list(state.hand):
            state.discard(c)
        state.emit(f"Balance: sacrifice {len(lands)} land(s) + {len(creatures)} "
                   f"creature(s), discard {n_hand} card(s)")
