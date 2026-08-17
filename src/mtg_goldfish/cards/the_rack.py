"""The Rack — {1} Artifact.
As this artifact enters, choose an opponent. At the beginning of the chosen
player's upkeep, it deals X damage to them, where X is 3 minus the cards in their
hand.

Entirely opponent-facing: it damages the chosen opponent on THEIR upkeep, and the
phantom opponent in a goldfish has no upkeep/hand — so it never does anything. A
fixed artifact here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TheRack(Card):
    card_name = "The Rack"
