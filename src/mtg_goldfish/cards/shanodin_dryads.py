"""Shanodin Dryads
{G} Creature — Nymph Dryad 1/1. Forestwalk.

Forestwalk is evasion — inert with no opponent to be walked past — so effectively
a vanilla 1/1."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ShanodinDryads(Card):
    card_name = "Shanodin Dryads"
