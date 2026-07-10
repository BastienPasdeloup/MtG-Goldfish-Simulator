"""Veil of Summer — {G} Instant.
Its effects are all reactive to opponents (draw if an opponent cast blue/black;
anti-counter; hexproof from blue/black). None of them do anything in a
solitaire game, but the spell is still legally castable — it needs no target —
so it can be cast and simply resolves to the graveyard doing nothing."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class VeilOfSummer(Card):
    card_name = "Veil of Summer"
    # No overrides: castable via the engine default; resolves with no effect.
