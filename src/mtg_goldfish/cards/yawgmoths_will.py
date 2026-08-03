"""Yawgmoth's Will — {2}{B} Sorcery. Until end of turn, you may play lands and
cast spells from your graveyard. If a card would be put into your graveyard from
anywhere this turn, exile it instead (so each graveyard card is replayed once)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class YawgmothsWill(Card):
    card_name = "Yawgmoth's Will"

    def on_resolve(self, state):
        state.gy_play_all = True
        state.gy_exile_replace = True
        state.emit("Yawgmoth's Will: play lands and cast spells from your graveyard "
                   "this turn (cards to graveyard are exiled instead)")
        return None
