"""Phyrexian Gremlins — {2}{B} Creature — Phyrexian Gremlin 1/1.
You may choose not to untap this creature during your untap step.
{T}: Tap target artifact. It doesn't untap during its controller's untap step for
as long as this creature remains tapped.

The ability is artifact hate aimed at OPPONENTS' artifacts; in a goldfish the only
legal targets are your own artifacts, and tap-locking your own artifact is never
beneficial, so the search would never use it. Registered as a fixed 1/1 body — the
ability is left inert rather than bloating the search with a strictly-negative
option."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class PhyrexianGremlins(Card):
    card_name = "Phyrexian Gremlins"
