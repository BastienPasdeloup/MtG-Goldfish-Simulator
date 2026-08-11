"""Shield Sphere — {0} Artifact Creature — Wall 0/6.
Defender. Whenever this creature blocks, put a -0/-1 counter on it.

Defender + the block trigger only matter on defence; a solitaire goldfish is
never attacked, so it plays as a free 0/6 artifact creature (artifact count /
sacrifice fodder)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ShieldSphere(Card):
    card_name = "Shield Sphere"
