"""Ironclaw Orcs
{1}{R} Creature — Orc 2/2.
This creature can't block creatures with power 2 or greater.

The blocking restriction is inert in a solitaire goldfish (nothing to block), so
this is effectively a 2/2 vanilla body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IronclawOrcs(Card):
    card_name = "Ironclaw Orcs"
