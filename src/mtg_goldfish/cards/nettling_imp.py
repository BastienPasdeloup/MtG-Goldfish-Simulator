"""Nettling Imp — {2}{B} Creature — Imp 1/1.
{T}: Choose target non-Wall creature the active player has controlled ... That
creature attacks this turn if able ... Activate only during an opponent's turn.

The ability can only be used on an opponent's turn against their creatures — none
exist in a solitaire goldfish — so it is inert. A 1/1 body that still enters."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NettlingImp(Card):
    card_name = "Nettling Imp"
