"""Power Sink — {X}{U} Instant.
Counter target spell unless its controller pays {X}. If that player doesn't, they
tap all lands with mana abilities they control and lose all unspent mana.

Countering requires a spell on the stack; with atomic resolution there is never
one at a priority window, so this is uncastable. It is still cast (counting toward
spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PowerSink(Card):
    card_name = "Power Sink"
