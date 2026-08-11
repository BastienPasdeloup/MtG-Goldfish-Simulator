"""Mana Short — {2}{U} Instant.
Tap all lands target player controls and that player loses all unspent mana.

Purely disruptive against an opponent; targeting yourself is strictly bad, so the
spell is inert here. It is still cast (counting toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ManaShort(Card):
    card_name = "Mana Short"
