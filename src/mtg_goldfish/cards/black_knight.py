"""Black Knight — {B}{B} Creature — Human Knight 2/2. First strike; protection
from white. First strike (no blockers in a goldfish) and protection from white
(no white opponent sources) have no goldfish effect — a plain 2/2."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BlackKnight(Card):
    card_name = "Black Knight"
