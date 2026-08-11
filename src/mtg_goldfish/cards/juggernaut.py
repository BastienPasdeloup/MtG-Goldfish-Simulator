"""Juggernaut
{4} Artifact Creature — Juggernaut 5/3.
This creature attacks each combat if able.
This creature can't be blocked by Walls.

The "can't be blocked by Walls" clause is inert (no blockers in a goldfish). The
"attacks each combat if able" requirement is a drawback that rarely matters here
(attacking with a 5/3 is almost always the line the search wants anyway) and isn't
force-modelled — effectively a 5/3 artifact body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Juggernaut(Card):
    card_name = "Juggernaut"
