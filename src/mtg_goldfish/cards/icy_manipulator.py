"""Icy Manipulator — {4} Artifact.
{1}, {T}: Tap target artifact, creature, or land.

Tapping is only useful against an opponent's permanents (to deny attackers,
blockers, or mana) — there are none in a solitaire goldfish, and tapping your own
permanents is never beneficial — so the ability is inert. The artifact is still
cast and enters the battlefield (counting toward artifact/permanent counts)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class IcyManipulator(Card):
    card_name = "Icy Manipulator"
