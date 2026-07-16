"""Nezumi Linkbreaker — {B} Creature 1/1. When it dies, create a 1/1 red
Mercenary creature token (its own "{T}: target creature you control gets +1/+0"
pump ability is a marginal combat trick and is left as a vanilla token)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NezumiLinkbreaker(Card):
    card_name = "Nezumi Linkbreaker"

    def on_leave(self, state, permanent):
        state.make_token(
            "Mercenary", 1, 1, "Creature — Mercenary",
            text="{T}: Target creature you control gets +1/+0 until end of turn. "
                 "Activate only as a sorcery.")
        state.emit("Nezumi Linkbreaker: create a 1/1 Mercenary")
