"""Grim Initiate — {R} Creature 1/1, first strike. When it dies, amass Zombies 1."""
from __future__ import annotations

from ._common import amass
from .base import Card
from .registry import register


@register
class GrimInitiate(Card):
    card_name = "Grim Initiate"

    def on_leave(self, state, permanent):
        amass(state, 1, "Zombie")
