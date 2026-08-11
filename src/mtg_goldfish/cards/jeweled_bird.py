"""Jeweled Bird — {1} Artifact.
{T}: Ante this artifact. If you do, put all other cards you own from the ante into
your graveyard, then draw a card.

An ante card (only legal when playing for ante); the ante mechanics don't apply in
a goldfish, so it's a bare artifact that still enters (counting as a permanent)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class JeweledBird(Card):
    card_name = "Jeweled Bird"
