"""Vesuvan Doppelganger — {3}{U}{U} Creature — Shapeshifter 0/0.
You may have this creature enter as a copy of any creature on the battlefield
(it doesn't copy colour and gains an upkeep re-copy ability).

Modelled like Clone: one ETB branch per distinct creature to copy (plus declining
→ a 0/0 that dies). The copy is permanent and its ETB fires; the colour exception
and the upkeep re-copy ability are not modelled."""
from __future__ import annotations

from ._common import enter_as_copy
from .base import Card
from .registry import register


@register
class VesuvanDoppelganger(Card):
    card_name = "Vesuvan Doppelganger"

    def enter_choices(self, state, perm):
        return enter_as_copy(self, state, perm, lambda p: p.is_creature_now)
