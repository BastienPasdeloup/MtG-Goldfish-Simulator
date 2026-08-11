"""Rukh Egg — {3}{R} Creature — Bird Egg 0/3.
When this creature dies, create a 4/4 red Bird creature token with flying at the
beginning of the next end step.

When Rukh Egg leaves the battlefield (almost always by dying in a goldfish), a 4/4
red flying Bird token is created. The "at the next end step" delay isn't modelled —
the token is made immediately."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class RukhEgg(Card):
    card_name = "Rukh Egg"

    def on_leave(self, state, permanent):
        tok = state.make_token("Bird", 4, 4, "Creature — Bird",
                               text="Flying", colors=["R"])
        tok.extra_keywords.add("flying")
        state.emit("Rukh Egg: create a 4/4 red flying Bird")
