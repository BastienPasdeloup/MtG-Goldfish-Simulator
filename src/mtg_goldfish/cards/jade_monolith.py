"""Jade Monolith — {4} Artifact.
{1}: The next time a source of your choice would deal damage to target creature
this turn, that source deals that damage to you instead.

Redirecting damage from a creature to yourself is only situationally useful and
never beneficial in a solitaire goldfish, so the ability is left inert. The
artifact is still cast and enters (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class JadeMonolith(Card):
    card_name = "Jade Monolith"
