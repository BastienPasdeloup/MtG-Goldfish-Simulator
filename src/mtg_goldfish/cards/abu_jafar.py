"""Abu Ja'far — {W} Creature — Human 0/1.
When this creature dies, destroy all creatures blocking or blocked by it.

The death trigger only affects creatures in combat WITH it (blocking/blocked) —
there are none in a solitaire goldfish, so it's inert. A 0/1 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AbuJafar(Card):
    card_name = "Abu Ja'far"
