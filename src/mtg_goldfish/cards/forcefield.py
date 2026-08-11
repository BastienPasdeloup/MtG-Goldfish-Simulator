"""Forcefield — {3} Artifact.
{1}: The next time an unblocked creature of your choice would deal combat damage
to you this turn, prevent all but 1 of that damage.

Purely defensive against an attacking opponent — there is none in a solitaire
goldfish — so the ability is inert. The artifact is still cast and enters the
battlefield (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Forcefield(Card):
    card_name = "Forcefield"
