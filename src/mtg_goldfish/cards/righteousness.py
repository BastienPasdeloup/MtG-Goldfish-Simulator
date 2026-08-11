"""Righteousness — {W} Instant.
Target blocking creature gets +7/+7 until end of turn.

Only a BLOCKING creature can be targeted; there is no combat with blockers in a
solitaire goldfish, so this is inert. The spell is still cast (counting toward
spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Righteousness(Card):
    card_name = "Righteousness"
