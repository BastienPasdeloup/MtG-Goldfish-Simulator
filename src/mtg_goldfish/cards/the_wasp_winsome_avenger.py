"""The Wasp, Winsome Avenger — {1}{U} Legendary Creature — Human Hero 2/1.
Flash, flying (both handled by the engine from the card's keywords).

Both triggered abilities are benign no-ops in a goldfish, so they are not
modelled (no spurious stack items):
  * the ETB grants a target Hero hexproof until end of turn — the phantom
    opponent never targets our permanents;
  * the attack trigger taps a target creature the defending player controls —
    the phantom opponent controls no creatures.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class TheWaspWinsomeAvenger(Card):
    card_name = "The Wasp, Winsome Avenger"
