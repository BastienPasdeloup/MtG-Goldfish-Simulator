"""Blaze of Glory — {W} Instant.
Grants a defending player's creature the ability to block any number of creatures
(and forces it to block). Purely a DEFENSIVE combat trick against an attacker —
there is no opponent attacking you in a goldfish, so it has no effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BlazeOfGlory(Card):
    card_name = "Blaze of Glory"
