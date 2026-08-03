"""Valgavoth, Terror Eater — {6}{B}{B}{B} 9/9 Flying, lifelink. Ward—Sacrifice
three nonland permanents.
In a solitaire game its opponent-facing text (exile cards from opponents'
graveyards; play those exiled cards) never does anything, so it is modelled as
its body: a 9/9 flying lifelink beater / reanimation target."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ValgavothTerrorEater(Card):
    card_name = "Valgavoth, Terror Eater"
