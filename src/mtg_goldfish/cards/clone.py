"""Clone — {3}{U} Creature — Shapeshifter 0/0.
You may have this creature enter as a copy of any creature on the battlefield.

One ETB branch per distinct creature to copy (plus declining → a 0/0 that dies).
The copy is permanent and its ETB fires."""
from __future__ import annotations

from ._common import enter_as_copy
from .base import Card
from .registry import register


@register
class Clone(Card):
    card_name = "Clone"

    def enter_choices(self, state, perm):
        return enter_as_copy(self, state, perm, lambda p: p.is_creature_now)
