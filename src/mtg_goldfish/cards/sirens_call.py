"""Siren's Call — {U} Instant.
Cast this spell only during an opponent's turn, before attackers are declared.
Creatures the active player controls attack this turn if able ...

Only castable on an opponent's turn to force their creatures to attack — there is
no opponent in a solitaire goldfish, so it is inert. It is still cast (counting
toward spells cast)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class SirensCall(Card):
    card_name = "Siren's Call"
