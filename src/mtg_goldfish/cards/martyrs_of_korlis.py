"""Martyrs of Korlis — {3}{W}{W} Creature — Human 1/6.
As long as this creature is untapped, all damage that would be dealt to you by
artifacts is dealt to this creature instead.

Redirection is exposed via `redirects_artifact_damage`; `damage_self(by_artifact=
True)` sends the damage to the untapped Martyrs (its 6 toughness soaks Mana Vault /
Ankh / Copper Tablet pings)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class MartyrsOfKorlis(Card):
    card_name = "Martyrs of Korlis"

    def redirects_artifact_damage(self, state, perm):
        return True  # damage_self already checks `not perm.tapped`
