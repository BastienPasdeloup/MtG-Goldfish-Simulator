"""Fork — {R}{R} Instant.
Copy target instant or sorcery spell, except that the copy is red. You may choose
new targets for the copy.

Fork must target a spell ON THE STACK. This engine resolves spells atomically —
there is never another spell on the stack at a priority window — so Fork has no
legal target and its copy effect can't be modelled. It is still cast (counting
toward spells cast); this is a genuine structural limitation of a solitaire
atomic-resolution goldfish, not a missing implementation."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Fork(Card):
    card_name = "Fork"
