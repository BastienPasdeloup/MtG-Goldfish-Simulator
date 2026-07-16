"""Hexing Squelcher — {1}{R} Creature 2/2, ward—pay 2 life.
Its "can't be countered" clauses and the ward it grants have no effect against a
phantom opponent (nothing counters your spells and there are no attackers to
tax), so it plays as a vanilla 2/2 body."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class HexingSquelcher(Card):
    card_name = "Hexing Squelcher"
