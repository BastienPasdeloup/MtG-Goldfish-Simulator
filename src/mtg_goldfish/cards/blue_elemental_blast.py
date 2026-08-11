"""Blue Elemental Blast — {U} Instant.
Counter target red spell OR destroy target red permanent. Both need a red target
an opponent controls (or a red spell on the stack) — none exist in a solitaire
goldfish, so it has no effect (a rational player never targets their own)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BlueElementalBlast(Card):
    card_name = "Blue Elemental Blast"
