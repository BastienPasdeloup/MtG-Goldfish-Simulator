"""Eye for an Eye — {W}{W} Instant.
The next time a source of your choice would deal damage to you this turn, instead
that source deals that much damage to you and Eye for an Eye deals that much damage
to that source's controller.

It reflects damage to the source's CONTROLLER. In a solitaire goldfish every damage
source is controlled by you, so it would only reflect to yourself — inert. The
spell is still cast (counting toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class EyeForAnEye(Card):
    card_name = "Eye for an Eye"
