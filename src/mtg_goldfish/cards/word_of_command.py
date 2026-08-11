"""Word of Command — {B}{B} Instant.
Look at target opponent's hand and choose a card ... You control that player ...

Entirely opponent-controlling; there is no opponent in a solitaire goldfish, so it
is inert. It is still cast (counting toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WordOfCommand(Card):
    card_name = "Word of Command"
