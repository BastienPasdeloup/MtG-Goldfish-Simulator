"""Guardian Beast — {3}{B} Creature — Beast 2/4.
As long as this creature is untapped, noncreature artifacts you control can't be
enchanted, they have indestructible, and other players can't gain control of them.

The materially-relevant clause in a solitaire goldfish is INDESTRUCTIBLE: while
Guardian Beast is untapped, your noncreature artifacts survive destruction /
board wipes (via `protects_artifacts`, checked in _survives_destruction). The
can't-be-enchanted / can't-be-stolen clauses are opponent-facing and inert."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GuardianBeast(Card):
    card_name = "Guardian Beast"

    def protects_artifacts(self, state, perm):
        return not perm.tapped
