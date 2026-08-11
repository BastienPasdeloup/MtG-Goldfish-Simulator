"""Pithing Needle — {1} Artifact.
As this artifact enters, choose a card name.
Activated abilities of sources with the chosen name can't be activated unless
they're mana abilities.

A hate card aimed at an opponent's cards; a rational solitaire player never names
their own, so it has no goldfish effect and plays as a {1} artifact (counts for
affinity / Emry / improvise)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PithingNeedle(Card):
    card_name = "Pithing Needle"
