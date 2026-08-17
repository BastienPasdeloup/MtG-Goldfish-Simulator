"""Powerleech — {G}{G} Enchantment.
Whenever an artifact an opponent controls becomes tapped or an opponent activates
an artifact's ability without {T} in its activation cost, you gain 1 life.

Keys entirely off OPPONENTS' artifacts; the phantom opponent controls none in a
goldfish, so it never triggers. A fixed enchantment here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Powerleech(Card):
    card_name = "Powerleech"
