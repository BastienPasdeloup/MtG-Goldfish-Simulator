"""Thicket Basilisk
{3}{G}{G} Creature — Basilisk 2/4.
Whenever this creature blocks or becomes blocked by a non-Wall creature, destroy
that creature at end of combat.

The deathtouch-on-block clause is inert with no blockers/blocking in a solitaire
goldfish. A 2/4 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ThicketBasilisk(Card):
    card_name = "Thicket Basilisk"
