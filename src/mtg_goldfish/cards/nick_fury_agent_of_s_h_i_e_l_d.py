"""Nick Fury, Agent of S.H.I.E.L.D. — Legendary Creature — Human Spy Hero.

Best-effort implementation: the engine models this card being cast/entering and
counting toward board state and spell tallies, but its special rules text is not
simulated yet.
"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class NickFuryAgentOfSHIELD(Card):
    card_name = 'Nick Fury, Agent of S.H.I.E.L.D.'
