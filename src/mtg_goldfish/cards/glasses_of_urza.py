"""Glasses of Urza — {1} Artifact.
{T}: Look at target player's hand.

Pure information, and there is no opponent hand to look at in a solitaire
goldfish, so the ability is inert — the artifact is still cast and enters the
battlefield (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GlassesOfUrza(Card):
    card_name = "Glasses of Urza"
