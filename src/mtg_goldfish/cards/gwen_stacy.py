"""Gwen Stacy // Ghost-Spider — {1}{R} Legendary Creature 2/1.
ETB: exile the top card of your library; you may play it for as long as you
control Gwen. {2}{U}{R}{W}: transform (sorcery). Ghost-Spider's own counter
abilities (counter on exile-play; remove 2: impulse) are not modelled —
documented approximation."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card
from .registry import register


@register
class GwenStacy(Card):
    card_name = "Gwen Stacy // Ghost-Spider"
    exiles_cards = True

    def on_etb(self, state, permanent):
        if state.library:
            card = state.library.pop(0)
            state.exile.append(card)
            state.exile_playable.append((permanent.uid, card))
            state.emit(f"Gwen Stacy: exile {card.name} — playable while she remains")
        return None

    def link_exiled_card(self, state, perm, card):
        # Exiled with Gwen -> you may play it from exile while she remains.
        state.exile_playable.append((perm.uid, card))

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=2, pips=(("U", 1), ("R", 1), ("W", 1))),
            "Ghost-Spider",
        )
