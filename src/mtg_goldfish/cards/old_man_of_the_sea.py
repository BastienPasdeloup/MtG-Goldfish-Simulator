"""Old Man of the Sea — {1}{U}{U} Creature — Djinn 2/3.
You may choose not to untap this creature during your untap step.
{T}: Gain control of target creature with power <= this creature's power ...

Stealing control only matters against an opponent's creature — there are none in a
solitaire goldfish — so the ability is inert. A 2/3 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class OldManOfTheSea(Card):
    card_name = "Old Man of the Sea"
