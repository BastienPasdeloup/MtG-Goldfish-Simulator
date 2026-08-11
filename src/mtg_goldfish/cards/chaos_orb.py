"""Chaos Orb
{2} Artifact — flip it physically to destroy permanents it touches.
A dexterity effect that can't be modelled in a simulator — a {2} artifact."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ChaosOrb(Card):
    card_name = "Chaos Orb"
