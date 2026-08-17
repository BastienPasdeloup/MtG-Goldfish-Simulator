"""Citanul Druid — {1}{G} Creature — Human Druid 1/1.
Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature.

The trigger keys off an OPPONENT casting — the phantom opponent never casts in a
goldfish, so it never fires: a fixed 1/1 body here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class CitanulDruid(Card):
    card_name = "Citanul Druid"
