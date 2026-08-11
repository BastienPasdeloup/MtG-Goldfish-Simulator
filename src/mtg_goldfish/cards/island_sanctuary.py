"""Island Sanctuary — {1}{W} Enchantment.
If you would draw a card during your draw step, instead you may skip that draw. If
you do, until your next turn, you can't be attacked except by creatures with
flying and/or islandwalk.

Purely defensive against an attacking opponent — there is none in a solitaire
goldfish — and skipping your draw is strictly bad here, so both clauses are inert.
The enchantment is still cast and enters (counting toward enchantment/permanent
counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IslandSanctuary(Card):
    card_name = "Island Sanctuary"
