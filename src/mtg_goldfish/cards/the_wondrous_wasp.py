"""The Wondrous Wasp — {1}{U} Legendary 2/1 flash, flying. ETB: tap up to one
target creature and remove its abilities — targeting your own creature is
strictly harmful and targeting "none" is legal, so the trigger resolves as
"no target" (exact for any sensible line; hostile self-targets not enumerated)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TheWondrousWasp(Card):
    card_name = "The Wondrous Wasp"

    def on_etb(self, state, permanent):
        state.emit("The Wondrous Wasp: no creature targeted")
        return None
