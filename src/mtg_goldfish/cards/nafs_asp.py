"""Nafs Asp — {G} Creature — Snake 1/1.
Whenever this creature deals damage to a player, that player loses 1 life at the
beginning of their next draw step unless they pay {1}.

The delayed drain only affects the opponent (who has no hand/decisions modelled)
and is a small extra to combat damage the goldfish already applies — left inert.
A 1/1 body."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class NafsAsp(Card):
    card_name = "Nafs Asp"
