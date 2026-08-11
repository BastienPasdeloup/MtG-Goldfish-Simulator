"""Oasis — Land.
{T}: Prevent the next 1 damage that would be dealt to target creature this turn.

Produces no mana; only prevents 1 damage to a creature (marginal, and it can't help
you race). Left as a bare land that still plays (counting as a land)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class Oasis(Card):
    card_name = "Oasis"
