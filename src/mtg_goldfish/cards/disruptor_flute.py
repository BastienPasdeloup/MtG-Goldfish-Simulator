"""Disruptor Flute — {2} Artifact. Flash.
As this artifact enters, choose a card name.
Spells with the chosen name cost {3} more to cast.
Activated abilities of sources with the chosen name can't be activated unless
they're mana abilities.

Both effects target an OPPONENT's cards; a rational player never names their own.
With no opponent in a solitaire goldfish there is nothing to name, so it plays as
a {2} artifact (with flash) that counts toward artifact synergies (affinity,
Emry, improvise). The name choice is a real ability but has no goldfish effect."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DisruptorFlute(Card):
    card_name = "Disruptor Flute"
