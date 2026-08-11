"""Jade Statue — {4} Artifact.
{2}: This artifact becomes a 3/6 Golem artifact creature until end of combat.
Activate only during combat.

Animated via the shared `becomes` mechanism (3/6 until cleanup — the
combat-only timing isn't enforced; the search animates it when it wants to
attack). Reuses `animate_land_action` (works on any permanent)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import animate_land_action
from .base import Card
from .registry import register


@register
class JadeStatue(Card):
    card_name = "Jade Statue"

    def battlefield_actions(self, state, perm):
        return animate_land_action(
            self, state, perm,
            cost=ManaCost(generic=2),
            type_line="Artifact Creature — Golem",
            power=3, toughness=6,
            label="Jade Statue: become a 3/6 Golem",
        )
