"""Cursed Rack — {4} Artifact.
As this artifact enters, choose an opponent. The chosen player's maximum hand size
is four.

Purely opponent-facing (limits the chosen opponent's hand size); the phantom
opponent has no hand in a goldfish, so it never does anything. A fixed artifact."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CursedRack(Card):
    card_name = "Cursed Rack"
