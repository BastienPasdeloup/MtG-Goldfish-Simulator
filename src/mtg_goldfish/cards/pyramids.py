"""Pyramids — {6} Artifact.
{2}: Destroy target Aura attached to a land; or prevent the next destruction of a
target land this turn.

Both modes are defensive/situational (removing an Aura from your land, or saving a
land from destruction) and rarely relevant in a goldfish. Left as a bare artifact
that still enters (counting as a permanent)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class Pyramids(Card):
    card_name = "Pyramids"
