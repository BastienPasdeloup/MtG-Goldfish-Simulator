"""Raging River — {R}{R} Enchantment.
Whenever one or more creatures you control attack, each defending player divides
their creatures into "left"/"right" piles ...

A combat pile-division evasion effect that depends on an opponent's blockers, of
which there are none in a solitaire goldfish, so it is inert. The enchantment is
still cast and enters (counting toward enchantment/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class RagingRiver(Card):
    card_name = "Raging River"
