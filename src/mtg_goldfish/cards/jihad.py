"""Jihad — {W}{W}{W} Enchantment.
As this enchantment enters, choose a color and an opponent. White creatures get
+2/+1 as long as the chosen player controls a nontoken permanent of the chosen
color. When the chosen player controls no such permanent, sacrifice Jihad.

The chosen opponent controls no permanents in a solitaire goldfish, so the anthem
never turns on (and it would immediately be sacrificed). Left as a bare enchantment
that still enters (counting as a permanent)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Jihad(Card):
    card_name = "Jihad"
