"""Personal Incarnation — {3}{W}{W}{W} Creature — Avatar Incarnation 6/6.
{0}: The next 1 damage that would be dealt to this creature this turn is dealt to
its owner instead.
When this creature dies, its owner loses half their life, rounded up.

A 6/6 with a steep death clause: when it leaves the battlefield you lose half your
life (rounded up). The damage-redirect ability (to yourself) is never beneficial
in a goldfish and is left inert."""
from __future__ import annotations

import math

from .base import Card
from .registry import register


@register
class PersonalIncarnation(Card):
    card_name = "Personal Incarnation"

    def on_leave(self, state, permanent):
        loss = math.ceil(state.life / 2)
        state.life -= loss
        state.emit(f"Personal Incarnation dies: lose half your life ({loss})")
