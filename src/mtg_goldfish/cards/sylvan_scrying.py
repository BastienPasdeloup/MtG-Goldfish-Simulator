"""Sylvan Scrying — {1}{G} Sorcery.
Search your library for a land card, reveal it, put it into your hand, then
shuffle (one branch per distinct land in the library)."""
from __future__ import annotations

from ._common import tutor_to_hand_branches
from .base import Card
from .registry import register


@register
class SylvanScrying(Card):
    card_name = "Sylvan Scrying"

    def on_resolve(self, state):
        return tutor_to_hand_branches(state, lambda c: c.is_land, note=" (Sylvan Scrying)")
