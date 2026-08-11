"""Spell Blast — {X}{U} Instant.
Counter target spell with mana value X.

Countering requires a spell on the stack; with atomic resolution there is never
one at a priority window, so this is uncastable. It is still cast (counting toward
spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SpellBlast(Card):
    card_name = "Spell Blast"
