"""Stone Giant
{2}{R}{R} Creature — Giant 3/4.
{T}: Target creature you control with toughness less than this creature's power
gains flying until end of turn. Destroy that creature at the beginning of the next
end step.

The ability grants flying (inert evasion) then destroys your own creature — never
beneficial in a solitaire goldfish — so it is left inert. A 3/4 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class StoneGiant(Card):
    card_name = "Stone Giant"
