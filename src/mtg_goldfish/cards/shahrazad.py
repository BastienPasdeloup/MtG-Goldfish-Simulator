"""Shahrazad — {W}{W} Sorcery.
Players play a Magic subgame, using their libraries as their decks. Each player who
doesn't win the subgame loses half their life, rounded up.

The subgame itself isn't simulated. It resolves as a branch over WHO wins it: if
YOU win, the (phantom) opponent loses half their life (rounded up); if the opponent
wins, you lose half your life. (Halving is life LOSS, not damage, so prevention
doesn't apply.)"""
from __future__ import annotations

import math

from ._common import branch_over
from .base import Card
from .registry import register


@register
class Shahrazad(Card):
    card_name = "Shahrazad"

    def on_resolve(self, state):
        def fn(st, opt):
            if opt == "you_win":
                loss = math.ceil(max(0, st.opponent_life) / 2)
                st.opponent_life -= loss
                st.emit(f"Shahrazad: you win the subgame — opponent loses {loss} life")
                st.check_life_totals()
            else:
                loss = math.ceil(max(0, st.life) / 2)
                st.life -= loss
                st.emit(f"Shahrazad: opponent wins the subgame — you lose {loss} life")
                st.check_life_totals()
            return None

        return branch_over(state, ["you_win", "opp_win"], fn)
