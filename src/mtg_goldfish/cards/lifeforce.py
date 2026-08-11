"""Lifeforce — {G}{G} Enchantment.
{G}{G}: Counter target black spell.

Countering requires a black spell on the stack; with atomic spell resolution
there is never one at a priority window, so the ability is uncastable. The
enchantment is still cast and enters (counting toward enchantment/permanent
counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Lifeforce(Card):
    card_name = "Lifeforce"
