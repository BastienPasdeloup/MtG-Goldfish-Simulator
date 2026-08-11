"""Hypnotic Specter
{1}{B}{B} Creature — Specter 2/2. Flying.
Whenever this creature deals damage to an opponent, that player discards a card
at random.

Flying is auto from the keyword. The combat-damage trigger targets the opponent's
HAND, which isn't modelled in a solitaire goldfish (no opponent hand), so the
rider is inert — a 2/2 flyer here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HypnoticSpecter(Card):
    card_name = "Hypnotic Specter"
