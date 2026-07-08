"""Drannith Magistrate — {1}{W} 1/3. "Your opponents can't cast spells from
anywhere other than their hands" — opponent-facing static, no effect in a
solitaire game. The body is exact."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DrannithMagistrate(Card):
    card_name = "Drannith Magistrate"
