"""Dauthi Voidwalker — {B}{B} Creature 3/2, shadow.
Its replacement (opponents' cards are exiled with void counters) and its
"{T}, Sacrifice: play an exiled card without paying its cost" ability only ever
touch an opponent's cards, so against a phantom opponent Dauthi is an unblockable
3/2 body (shadow gives evasion, which does not matter with no blockers)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DauthiVoidwalker(Card):
    card_name = "Dauthi Voidwalker"
